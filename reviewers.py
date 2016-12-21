#! /usr/bin/env python
import argparse
from decimal import Decimal
import pydoc
import re
import subprocess

import python_lib.shell as shl


def ensure_str(data):
    if type(data) != str:
        return data.decode("utf-8")
    return data


def run_cmd(cmd):
    return ensure_str(subprocess.check_output(cmd.split(" "))).strip().split("\n")


def get_git_branches():
    cmd = "git branch"
    return [x.strip() for x in run_cmd(cmd)]


def get_git_user():
    cmd = "git config --get user.name"
    return run_cmd(cmd)[0]


def get_blame(filename, start, num_lines, branch):
    cmd = "git --no-pager blame -L {start},+{num_lines} {branch} -- {file}"
    cmd = cmd.format(start=start, num_lines=num_lines, branch=branch, file=filename)
    return run_cmd(cmd)


def get_diff_raw(branch):
    cmd = "git --no-pager diff --raw {branch}"
    cmd = cmd.format(branch=branch)
    return run_cmd(cmd)


def get_file_diff(from_name, to_name, branch):
    if to_name:
        cmd = "git --no-pager diff {branch} -- {to_name} -- {from_name}"
        cmd = cmd.format(branch=branch, from_name=from_name, to_name=to_name)
    else:
        cmd = "git --no-pager diff {branch} -- {file}"
        cmd = cmd.format(branch=branch, file=from_name)

    return run_cmd(cmd)


def read_diff_raw_line(line):
    diff_info = dict(line=line, reviewers={}, chunks=[], parts=line.split("\t"))
    diff_info["raw_info"] = diff_info["parts"][0]
    if not diff_info["raw_info"]:
        return diff_info

    diff_info["from_mode"], \
        diff_info["to_mode"], \
        diff_info["from_hash"], \
        diff_info["to_hash"], \
        diff_info["type_info"] = diff_info["raw_info"].split(" ")

    diff_info["type"] = diff_info["type_info"][0]

    diff_info["file"] = diff_info["parts"][1]

    if len(diff_info["parts"]) > 2:
        diff_info["to_file"] = diff_info["parts"][2]

    return diff_info


def get_code_chunks(diff_info, branch):
    diff = get_file_diff(diff_info["file"], diff_info.get("to_file"), branch)

    diff_info["chunks"] = []
    for line in diff:
        if "@@" not in line:
            continue

        line_chunk = line.split("@@")[1].split(" ")[1][1:]
        chunk = {}
        chunk["start_line"], chunk["num_lines"] = line_chunk.split(",")

        diff_info["chunks"].append(chunk)

    return diff_info


def get_blame_code_line(line):
    prefix, code_line = line.split(")", 1)
    _, _, line_num = prefix.rpartition(" ")
    return dict(line_num=line_num, code_line=code_line[1:])


def get_blame_reviewer(line):
    reviewer_name_parts = []
    reviewer_parts = line.split("(")[1].split(")")[0].split(" ")
    for part in reviewer_parts:
        if re.match("^[0-9]{4}\-[0-9]{1,2}\-[0-9]{1,2}$", part):
            break
        reviewer_name_parts.append(part.strip())
    return " ".join(reviewer_name_parts).strip()


def get_blame_data(diff_info, branch):
    for chunk in diff_info["chunks"]:
        blame_info = get_blame(diff_info["file"], chunk["start_line"], chunk["num_lines"], branch)

        for line in blame_info:
            if "(" not in line or ")" not in line:
                continue

            code_line = get_blame_code_line(line)
            reviewer = get_blame_reviewer(line)

            if reviewer not in diff_info["reviewers"]:
                diff_info["reviewers"][reviewer] = []

            diff_info["reviewers"][reviewer].append(code_line)

    return diff_info


def get_file_reviewers(line, branch):

    diff_info = read_diff_raw_line(line)
    if diff_info.get("type") in ("A", None):
        return diff_info # Do not get reviewers on a new file

    diff_info = get_code_chunks(diff_info, branch)

    diff_info = get_blame_data(diff_info, branch)

    return diff_info


def get_total_reviewers(diff_infos):
    total_reviewers = {}
    current_user = get_git_user()
    for diff_info in diff_infos:
        for reviewer in diff_info["reviewers"]:
            if current_user.strip() == reviewer:
                continue # Don't include the current user

            if reviewer not in total_reviewers:
                total_reviewers[reviewer] = 0

            total_reviewers[reviewer] += len(diff_info["reviewers"][reviewer])

    total_reviewers_list = zip(total_reviewers.keys(), total_reviewers.values())
    total_reviewers_list = [list(x) for x in total_reviewers_list]
    total_reviewers_list = sorted(total_reviewers_list, key=lambda k: k[1], reverse=True)

    total_lines = sum(reviewer[1] for reviewer in total_reviewers_list)
    for reviewer in total_reviewers_list:
        reviewer.append(round((Decimal(reviewer[1]) / total_lines) * 100, 2))

    return total_reviewers_list


def print_suggested_reviewers(diff_infos):
    total_reviewers = get_total_reviewers(diff_infos)

    shl.print_section(shl.BOLD, "Suggested Reviewers:")

    # shl.print_table(["User", "Contributed", "Number of Lines"], total_reviewers)
    for reviewer in total_reviewers:
        shl.stdout("{user: >30}\t\t\t(Contrib: {percent: >5}%   Lines: {lines})".format(user=reviewer[0], percent=reviewer[2], lines=reviewer[1]))
    shl.stdout()


def print_contributer_lines(contributer, diff_infos):
    output = []
    for diff_info in diff_infos:
        lines = diff_info["reviewers"].get(contributer)
        if not lines:
            continue

        shl.print_section(shl.BOLD, diff_info["from_hash"], diff_info["file"], file=output)

        prev_line = None
        for line in lines:
            try:
                from pygments import highlight
                from pygments.lexers import PythonLexer
                from pygments.formatters import TerminalFormatter

                code = highlight(line["code_line"], PythonLexer(), TerminalFormatter())
            except ImportError:
                code = line["code_line"]

            cur_line = int(line["line_num"])

            if prev_line and prev_line + 1 < cur_line:
                output.append("    .")
                output.append("    .")
                output.append("    .")
            output.append("{line_num: >5}|\t{code_line}".format(line_num=line["line_num"], code_line=code.rstrip()))

            prev_line = cur_line

        output.append("\n\n")

    pydoc.pager("\n".join(output))


def get_reviewers(contributer, branch):
    raw = get_diff_raw(branch)
    shl.print_section(shl.BOLD, "Diff Raw Output:")
    diff_infos = []
    for diff in raw:
        diff_info = get_file_reviewers(diff, branch)
        if not diff_info.get("type"):
            continue
        diff_infos.append(diff_info)
        if diff_info["type"] == "A":
            shl.print_color(shl.GREEN, diff)
        elif diff_info["type"] == "D":
            shl.print_color(shl.RED, diff)
        elif diff_info["type"] == "M":
            shl.print_color(shl.YELLOW, diff)
        else:
            shl.print_color(shl.LTBLUE, diff)

    if contributer:
        print_contributer_lines(contributer, diff_infos)
    else:
        print_suggested_reviewers(diff_infos)
