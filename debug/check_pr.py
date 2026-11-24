"""Check what a pull request changes on the (virtual) spectrometer.

    python debug/check_pr.py 8                                  # GitHub PR #8
    python debug/check_pr.py pr/05-sensor-read-nan              # a branch (base from its PR)
    python debug/check_pr.py pr/05-sensor-read-nan --base version-1
    python debug/check_pr.py . --base version-1                 # your uncommitted working tree

What it does:
  1. Finds the PR's branch and the branch it merges into (with the GitHub CLI `gh`, or --base).
  2. Builds the result of the merge (base + PR) in a temporary worktree, the code that would
     be on the base branch after merging. Your checkout, branches and refs are not touched.
     If the merge would conflict, it lists the files and stops (or use --no-merge).
  3. Runs fake_hardware_harness.py from THIS folder on the base and on the merge result:
     every lab script end-to-end on the virtual rig (virtual_rig.py), the same scripts with
     instrument faults, and driver-level scenarios. All commands sent to every instrument
     are recorded.
  4. Reports every difference, per scenario and per instrument.

Each difference is either an intended effect of the PR (fine) or a regression (a problem).
The report can't tell which. That's the reviewer's call.

Options:
  --base BRANCH   branch the PR merges into (default: the PR's base on GitHub)
  --no-merge      compare the PR branch as it is instead of the merge result
  --report FILE   also write the report as Markdown (for pasting into the PR)
  --full          don't shorten long diffs
Exit code: 0 no differences, 1 differences found, 2 could not run (bad ref, conflict, ...).
"""
import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HARNESS = os.path.join(HERE, "fake_hardware_harness.py")
DIFF_LINES = 60


class Stop(Exception):
    pass


# ----------------------------------------------------------------------------- git / gh
def run(cmd, cwd, check=True):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                            errors="replace")
    if check and result.returncode != 0:
        raise Stop(f"{' '.join(cmd)} failed:\n{result.stderr.strip() or result.stdout.strip()}")
    return result


def git(repo, *args, check=True):
    return run(["git", *args], repo, check).stdout.strip()


def gh_exe():
    found = shutil.which("gh")
    default = r"C:\Program Files\GitHub CLI\gh.exe"
    return found or (default if os.path.exists(default) else None)


def gh_pr(repo, selector):
    """PR details from GitHub, or None if gh is missing or there's no such PR."""
    gh = gh_exe()
    if not gh:
        return None
    result = run([gh, "pr", "view", str(selector), "--json",
                  "number,title,url,baseRefName,headRefName,headRefOid"], repo, check=False)
    return json.loads(result.stdout) if result.returncode == 0 else None


def resolve(repo, ref):
    """A commit for ref, trying origin/<ref> when there's no local ref of that name."""
    for candidate in (ref, f"origin/{ref}"):
        result = run(["git", "rev-parse", "--verify", "--quiet", candidate + "^{commit}"], repo, False)
        if result.returncode == 0:
            return result.stdout.strip()
    raise Stop(f"Unknown git ref {ref!r} (also tried origin/{ref}). Try `git fetch` first.")


def find_target(repo, target, base_arg):
    """Return (description, base name, base commit, head commit or None for working tree)."""
    info = None
    if target.isdigit():
        info = gh_pr(repo, target)
        if info is None and not base_arg:
            raise Stop(f"Couldn't look up PR #{target} (is the GitHub CLI `gh` installed and "
                       f"signed in?). Pass the branch it merges into with --base.")
        git(repo, "fetch", "--quiet", "origin", f"pull/{target}/head")
        head = git(repo, "rev-parse", "FETCH_HEAD")
        label = f"PR #{target}" + (f" \"{info['title']}\" ({info['headRefName']})" if info else "")
    elif target == ".":
        if not base_arg:
            branch = git(repo, "branch", "--show-current")
            info = gh_pr(repo, branch) if branch else None
            if info is None:
                raise Stop("Pass the branch to compare your working tree with, e.g. --base version-1")
        head, label = None, "your working tree (uncommitted changes included)"
    else:
        head = resolve(repo, target)
        if not base_arg:
            info = gh_pr(repo, target)
            if info is None:
                raise Stop(f"No open PR found for {target!r}. Pass the branch it merges into with --base.")
        label = target + (f" (PR #{info['number']} \"{info['title']}\")" if info else "")
    base_name = base_arg or info["baseRefName"]
    run(["git", "fetch", "--quiet", "origin", base_name], repo, check=False)  # newest base if possible
    return label, base_name, resolve(repo, base_name), head


def merge_preview(repo, base, head):
    """Commit object for base + head merged; nothing in the repo points at it."""
    result = run(["git", "merge-tree", "--write-tree", "--name-only", "--no-messages", base, head],
                 repo, check=False)
    lines = result.stdout.strip().splitlines()
    if result.returncode == 1:
        raise Stop("The PR doesn't merge cleanly into its base. Conflicting files:\n  "
                   + "\n  ".join(lines[1:]) + "\nResolve the conflicts, or use --no-merge.")
    if result.returncode != 0:
        raise Stop(f"git merge-tree failed:\n{result.stderr.strip()}")
    return git(repo, "commit-tree", lines[0], "-p", base, "-p", head, "-m", "check_pr merge preview")


# ----------------------------------------------------------------------------- comparing
def comparable(result):
    """The result without keys that are shown but not compared (they start with "_")."""
    if isinstance(result, dict):
        return {k: v for k, v in result.items() if not k.startswith("_")}
    return result


def same(old, new, name):
    return comparable(old.get(name)) == comparable(new.get(name))


def outcome(result):
    if result is None:
        return "not run (scenario doesn't exist on this side)"
    if result.get("skipped"):
        return "skipped: " + result["skipped"]
    if result.get("stopped_by_rig"):
        return "ran until the rig's limit (" + result["stopped_by_rig"] + ")"
    if result.get("ok"):
        return "completed"
    where = ""
    if result.get("where"):
        file, _, function = result["where"].partition(" in ")
        line = f":{result['_line']}" if result.get("_line") else ""
        where = f" at {file}{line} in {function}"
    return f"raised {result['error']}: {result.get('msg', '')}{where}"


def instrument_of(event):
    return re.sub(r"^\[x\d+\] ", "", event).split(":", 1)[0]


def flatten(value, prefix=""):
    if isinstance(value, dict):
        lines = []
        for key in sorted(value, key=str):
            lines += flatten(value[key], f"{prefix}.{key}" if prefix else str(key))
        return lines or [f"{prefix} = {{}}"]
    if isinstance(value, list) and value and any(isinstance(v, (dict, list)) for v in value):
        lines = []
        for i, item in enumerate(value):
            lines += flatten(item, f"{prefix}[{i}]")
        return lines
    return [f"{prefix} = {json.dumps(value, default=str)}"]


def udiff(old, new, full):
    lines = list(difflib.unified_diff(old, new, "base", "with PR", n=2, lineterm=""))
    if not full and len(lines) > DIFF_LINES:
        lines = lines[:DIFF_LINES] + [f"... {len(lines) - DIFF_LINES} more diff lines (use --full)"]
    return lines


def compare_scenario(old, new, full):
    """List of (heading, diff lines) for one scenario."""
    sections = []
    if outcome(comparable(old)) != outcome(comparable(new)):
        sections.append(("outcome", [f"- base:    {outcome(old)}", f"+ with PR: {outcome(new)}"]))
    if old is None or new is None:
        return sections
    if "events" in old or "events" in new:
        ev_old, ev_new = old.get("events", []), new.get("events", [])
        instruments = sorted({instrument_of(e) for e in ev_old + ev_new})
        any_instrument = False
        for name in instruments:
            a = [e for e in ev_old if instrument_of(e) == name]
            b = [e for e in ev_new if instrument_of(e) == name]
            if a != b:
                any_instrument = True
                sections.append((f"commands to {name}", udiff(a, b, full)))
        if not any_instrument and ev_old != ev_new:
            sections.append(("order of commands across instruments", udiff(ev_old, ev_new, full)))
        seq_old = re.findall(r"seqc:([0-9a-f]{12})", "\n".join(ev_old))
        seq_new = re.findall(r"seqc:([0-9a-f]{12})", "\n".join(ev_new))
        for i, (a, b) in enumerate(zip(seq_old, seq_new)):
            if a != b:
                text_a = old["programs"].get(a, "").splitlines()
                text_b = new["programs"].get(b, "").splitlines()
                sections.append((f"SeqC program #{i + 1} uploaded to the HDAWG", udiff(text_a, text_b, full)))
        for key, heading in (("saves", "saved data (.mat)"), ("console", "printed output"),
                             ("warnings", "warnings")):
            a, b = flatten(old.get(key, [])), flatten(new.get(key, []))
            if key == "console":
                a, b = old.get("console", []), new.get("console", [])
            if a != b:
                sections.append((heading, udiff(a, b, full)))
    else:
        a, b = flatten(comparable(old)), flatten(comparable(new))
        if a != b:
            sections.append(("recorded result", udiff(a, b, full)))
    return sections


# ----------------------------------------------------------------------------- report
def report(header, old, new, full):
    names = sorted(set(old) | set(new))
    differ = [n for n in names if not same(old, new, n)]
    text = [f"Ran {len(names)} scenarios on each side: "
                     f"{len(names) - len(differ)} identical, {len(differ)} differ.", ""]
    md = ["## check_pr report", ""] + [f"    {h}" for h in header] + [
        "", f"**{len(names)} scenarios: {len(names) - len(differ)} identical, {len(differ)} differ.**", ""]
    if not differ:
        text.append("No differences: on the virtual rig the PR doesn't change anything the program does.")
        md.append("No differences: on the virtual rig the PR doesn't change anything the program does.")
        return text, md
    text.append("Differences. Check each one is an intended effect of the PR; any that isn't is a regression.")
    md.append("Check each difference is an intended effect of the PR; any that isn't is a regression.")
    for i, name in enumerate(differ, 1):
        sections = compare_scenario(old.get(name), new.get(name), full)
        text += ["", f"{i}. {name}"]
        md += ["", f"<details><summary><b>{i}. {name}</b> ({', '.join(h for h, _ in sections)})</summary>", ""]
        if outcome(comparable(old.get(name))) == outcome(comparable(new.get(name))):
            text.append(f"   outcome (both): {outcome(new.get(name))}")
            md.append(f"Outcome (both): {outcome(new.get(name))}")
        for heading, lines in sections:
            text.append(f"   {heading}:")
            text += [f"     {line}" for line in lines]
            md += ["", f"**{heading}**", "```diff", *lines, "```"]
        md += ["", "</details>"]
    summary = (f"{len(differ)} scenario(s) behave differently with the PR. If every difference "
               f"is intended, the PR is fine. If not, it's a regression.")
    return text + ["", summary], md + ["", summary]


def run_harness(roots, tmp):
    procs, outs = [], []
    for label, root in roots:
        out = os.path.join(tmp, f"{label}.json")
        outs.append(out)
        procs.append(subprocess.Popen([sys.executable, "-X", "utf8", HARNESS, root, out],
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                      encoding="utf-8", errors="replace"))
    results = []
    for (label, _), proc, out in zip(roots, procs, outs):
        log, _ = proc.communicate()
        if proc.returncode != 0:
            raise Stop(f"The harness failed on the {label} side:\n{log[-3000:]}")
        with open(out, encoding="utf-8") as f:
            results.append(json.load(f))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", help="PR number, branch name, or . for your working tree")
    parser.add_argument("--base", help="branch the PR merges into (default: from GitHub)")
    parser.add_argument("--no-merge", action="store_true", help="compare the PR branch as it is")
    parser.add_argument("--report", help="also write a Markdown report to this file")
    parser.add_argument("--full", action="store_true", help="don't shorten long diffs")
    args = parser.parse_args()

    repo = git(HERE, "rev-parse", "--show-toplevel")
    tmp = tempfile.mkdtemp(prefix="epr_check_pr_")
    worktrees = []
    try:
        label, base_name, base, head = find_target(repo, args.target, args.base)
        header = [f"PR:    {label}" + (f" @ {head[:7]}" if head else ""),
                  f"base:  {base_name} @ {base[:7]}"]
        if head is None:
            new_root = repo
            header.append("tested: your working tree as it is (no merge)")
        else:
            if args.no_merge:
                tested = head
                header.append(f"tested: the PR branch as it is @ {head[:7]} (--no-merge)")
            else:
                tested = merge_preview(repo, base, head)
                header.append(f"tested: {base_name} with the PR merged in (merges cleanly)")
            new_root = os.path.join(tmp, "with_pr")
            git(repo, "worktree", "add", "--detach", "--quiet", new_root, tested)
            worktrees.append(new_root)
        base_root = os.path.join(tmp, "base")
        git(repo, "worktree", "add", "--detach", "--quiet", base_root, base)
        worktrees.append(base_root)

        print("\n".join(header))
        print("Running both sides on the virtual rig (about a minute)...", flush=True)
        old, new = run_harness([("base", base_root), ("with PR", new_root)], tmp)
    except Stop as error:
        print(f"check_pr: {error}", file=sys.stderr)
        return 2
    finally:
        for path in worktrees:
            run(["git", "worktree", "remove", "--force", path], repo, check=False)
        shutil.rmtree(tmp, ignore_errors=True)

    text, md = report(header, old, new, args.full)
    print("\n" + "\n".join(text))
    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write("\n".join(md) + "\n")
        print(f"\nMarkdown report written to {args.report}")
    return 1 if any(not same(old, new, n) for n in set(old) | set(new)) else 0


if __name__ == "__main__":
    sys.exit(main())
