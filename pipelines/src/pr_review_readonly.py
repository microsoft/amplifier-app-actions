'''Trusted helpers for pipelines/pr-review-readonly.dot.

This file is the authoring source for the four tool nodes of the read-only pull
request review pipeline. The DOT file embeds it verbatim (rendered by
render_pr_review_readonly.py) because a remote DOT materializer fetches the DOT
file only. It uses the Python standard library and the git CLI only, so nothing
is installed at run time.

Embedding constraints, enforced by the renderer and its tests: this source
contains no double-quote character, no backslash and no dollar sign. The DOT
string unescaper rewrites backslash sequences, and the pipeline engine expands
dollar tokens in tool commands, so either character would silently change the
script. Every command runs as python3 -I (isolated mode) reading this source
from a heredoc, so neither the working directory nor PYTHONPATH can shadow a
standard library module.

Four commands form a fixed, staged retrieval:

  collect    validate the trusted entry parameters, verify the pull request
             binding on the allowlisted GitHub repository, fetch exactly the
             expected head and base commits into a bare repository that stays
             on disk for the later stages, and build the first evidence: the
             diff, the complete merge base and head versions of every changed
             file, and a complete bounded inventory of every file at both
             commits (side, path, mode, object id, size).
  expand1    validate the first file selection returned by the model, read the
  expand2    requested files by exact object id from the retained repository,
             and print the next, larger evidence. expand2 does the same for
             the second round.
  finalize   validate the final review returned by the model against the
             trusted manifest and write the strict review-result.json report.

Every model answer is a strict JSON document that must echo a fresh nonce kept
only in the private manifest and shown to the model only in the delimiters of
the current evidence, so an inherited or stale answer can never be accepted.
Each tool overwrites the next response key with an empty string.

Nothing from the pull request is checked out, built, installed, imported or
executed: objects are read with git cat-file, ls-tree and diff under an
isolated git configuration with external diff and textconv disabled. Any
problem fails closed: the process exits non-zero and no report is written.

Limits that are inherent to this design, not defects: the files the model
selects are chosen from a bounded inventory (at most MAX_INVENTORY_BYTES, 192
KiB, of path listing for both trees; a larger repository is refused), so a
selection is a relevance judgement, never proof that every relevant file was
read. A changed submodule pointer (gitlink) is refused because its content
cannot be reviewed. Publishing the report is the last fallible step of
finalize, but no script can make a write plus a process exit atomic across a
hard kill: a host must treat review-result.json as valid only when the
pipeline run itself succeeded.
'''

import hashlib
import json
import os
import secrets
import shutil
import stat
import string
import subprocess
import sys
import unicodedata

NL = chr(10)
TAB = chr(9)
BACKSLASH = chr(92)
NUL = bytes([0])
DOLLAR = chr(36)
FULLWIDTH_DOLLAR = chr(65284)

REPORT_VERSION = 1
OUTPUT_DIR = '/project/.resolve/data'
OUTPUT_NAME = 'review-result.json'
WORK_DIR = '/tmp/amplifier-pr-review-readonly'
MANIFEST_NAME = 'manifest.json'
MANIFEST_KIND = 'amplifier-pr-review-readonly/manifest'
MANIFEST_VERSION = 2
DATA_BEGIN = 'BEGIN UNTRUSTED PULL REQUEST DATA '
DATA_END = 'END UNTRUSTED PULL REQUEST DATA '

PR_CONTEXT_KEYS = frozenset(
    ('repository', 'pr_number', 'pr_url', 'action', 'head_sha', 'base_sha', 'base_ref')
)
ALLOWED_ACTIONS = frozenset(('opened', 'synchronize', 'reopened', 'ready_for_review'))

# Stages recorded in the private manifest.
STAGE_SELECT1 = 'select1'
STAGE_SELECT2 = 'select2'
STAGE_REVIEW = 'review'
STAGE_FINALIZED = 'finalized'
STAGES = (STAGE_SELECT1, STAGE_SELECT2, STAGE_REVIEW, STAGE_FINALIZED)

# Pipeline context keys (lowercase) and the environment names the engine
# exports for them through tool_env (uppercase).
EVIDENCE_KEYS = {1: 'pr_review_evidence_1', 2: 'pr_review_evidence_2', 3: 'pr_review_evidence_3'}
SELECT1_KEY = 'pr_review_select1_response'
SELECT2_KEY = 'pr_review_select2_response'
FINAL_KEY = 'pr_review_final_response'
SELECT1_ENV = SELECT1_KEY.upper()
SELECT2_ENV = SELECT2_KEY.upper()
FINAL_ENV = FINAL_KEY.upper()

# Input bounds.
MAX_PARAM_BYTES = 16384
MAX_ALLOWLIST_ENTRIES = 100

# Evidence bounds. Nothing is ever truncated: exceeding a bound refuses the
# review instead.
MAX_CHANGED_FILES = 200
MAX_FILE_BYTES = 262144
MAX_SELECTED_FILE_BYTES = 262144
MAX_DIFF_BYTES = 393216
MAX_EVIDENCE_BYTES = 458752
MAX_INVENTORY_BYTES = 196608
MAX_INVENTORY_ENTRIES = 20000
MAX_PATH_CHARS = 1024
MAX_REQUESTS = 12
MAX_REASON_CHARS = 300
MAX_SELECTION_BYTES = 65536
MAX_FINAL_BYTES = 32768
MAX_MANIFEST_BYTES = 1048576
REGULAR_MODES = ('100644', '100755')
SYMLINK_MODE = '120000'
SUBMODULE_MODE = '160000'

# Final review bounds (sized so the whole answer fits a 4096 token response).
MAX_MODEL_TITLE = 150
MAX_MODEL_SUMMARY = 1200
MAX_MODEL_REVIEW = 4500
MAX_CONTEXT_GAPS = 12
MAX_GAP_CHARS = 300
CONTEXT_SUFFICIENT = 'SUFFICIENT'
CONTEXT_INCOMPLETE = 'INCOMPLETE'
VERDICT_CONCLUSIONS = {'PASS': 'success', 'CHANGES_REQUESTED': 'failure'}
REVIEW_HEADINGS = ('Necessity', 'Layer fit', 'Pattern', 'Correctness', 'Calibration', 'Required changes')
NONE_BULLET = '- None'
NONE_MARKERS = frozenset(('none', 'no required changes', 'n/a'))

# The strict review-result.json contract, version 1.
REPORT_KEYS = ('version', 'repository', 'pr_number', 'head_sha', 'conclusion', 'title', 'summary', 'text')
REPORT_REQUIRED = frozenset(REPORT_KEYS[:-1])
REPORT_CONCLUSIONS = frozenset(('success', 'failure'))
MAX_REPORT_TITLE = 200
MAX_REPORT_SUMMARY = 16000
MAX_REPORT_TEXT = 32000
MAX_REPORT_BYTES = 65536

CAVEAT = (
    '> Automated read-only review. No code, tests, builds, installs or scripts '
    'from this pull request were executed; the findings come from reading the '
    'source at the exact head commit above, and no test result is claimed. '
    'Thorough but not definitive: a human maintainer should give final approval '
    'before merging.'
)

HEX = frozenset('0123456789abcdef')
OWNER_CHARS = frozenset(string.ascii_letters + string.digits + '-')
NAME_CHARS = frozenset(string.ascii_letters + string.digits + '-._')
BRANCH_CHARS = frozenset(string.ascii_letters + string.digits + '-._/')

# Environment variables that would redirect git to another repository, object
# store, executable or template. They are removed for every git invocation.
REDIRECTING_GIT_ENV = (
    'GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY',
    'GIT_ALTERNATE_OBJECT_DIRECTORIES', 'GIT_NAMESPACE', 'GIT_COMMON_DIR',
    'GIT_EXTERNAL_DIFF', 'GIT_DIFF_OPTS', 'GIT_REPLACE_REF_BASE', 'GIT_GRAFT_FILE',
    'GIT_SHALLOW_FILE', 'GIT_EXEC_PATH', 'GIT_TEMPLATE_DIR',
)


class ReviewError(Exception):
    '''A fail-closed refusal: no review is produced and the job fails.'''


# ---------------------------------------------------------------------------
# Strict JSON and identity validation
# ---------------------------------------------------------------------------


def _no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ReviewError('duplicate JSON key: ' + repr(key)[:80])
        result[key] = value
    return result


def _reject_constant(name):
    raise ReviewError('non-standard JSON constant: ' + name)


def strict_json(text, what, max_bytes=MAX_PARAM_BYTES):
    '''Parse JSON rejecting duplicate keys, NaN/Infinity and oversize input.'''
    if not isinstance(text, str) or not text:
        raise ReviewError(what + ' is missing')
    try:
        encoded = text.encode('utf-8')
    except UnicodeEncodeError:
        raise ReviewError(what + ' is not valid UTF-8 text') from None
    if len(encoded) > max_bytes:
        raise ReviewError(what + ' exceeds ' + str(max_bytes) + ' bytes')
    try:
        return json.loads(text, object_pairs_hook=_no_duplicate_keys, parse_constant=_reject_constant)
    except (ValueError, RecursionError):
        raise ReviewError(what + ' is not valid JSON') from None


def is_sha(value):
    return type(value) is str and len(value) == 40 and all(c in HEX for c in value)


def is_nonce(value):
    return type(value) is str and len(value) == 32 and all(c in HEX for c in value)


def is_repository(value):
    if type(value) is not str or value.count('/') != 1:
        return False
    owner, name = value.split('/')
    if not 1 <= len(owner) <= 39 or not set(owner) <= OWNER_CHARS:
        return False
    if owner.startswith('-') or owner.endswith('-'):
        return False
    if not 1 <= len(name) <= 100 or not set(name) <= NAME_CHARS:
        return False
    return name not in ('.', '..') and not name.lower().endswith('.git')


def is_branch(value):
    if type(value) is not str or not 1 <= len(value) <= 255:
        return False
    if not set(value) <= BRANCH_CHARS:
        return False
    if value.startswith(('/', '-', '.')) or value.endswith(('/', '.', '.lock')):
        return False
    if '..' in value or '//' in value:
        return False
    return all(part and not part.startswith('.') and not part.endswith('.lock') for part in value.split('/'))


def is_pr_number(value):
    return type(value) is int and 1 <= value <= 2147483647


def parse_inputs(pr_context_text, review_head_sha_text, allowlist_text):
    '''Validate the three trusted entry parameters and return the identity.'''
    pr = strict_json(pr_context_text, 'pr_context')
    if type(pr) is not dict:
        raise ReviewError('pr_context must be a JSON object')
    keys = set(pr)
    if keys != PR_CONTEXT_KEYS:
        missing = sorted(PR_CONTEXT_KEYS - keys)
        extra = sorted(keys - PR_CONTEXT_KEYS)
        raise ReviewError('pr_context keys mismatch; missing ' + repr(missing) + ', unexpected ' + repr(extra))
    repository = pr['repository']
    if not is_repository(repository):
        raise ReviewError('pr_context.repository is not a valid owner/name')
    if not is_pr_number(pr['pr_number']):
        raise ReviewError('pr_context.pr_number must be a positive integer')
    expected_url = 'https://github.com/' + repository + '/pull/' + str(pr['pr_number'])
    if pr['pr_url'] != expected_url:
        raise ReviewError('pr_context.pr_url does not match repository and pr_number')
    if pr['action'] not in ALLOWED_ACTIONS:
        raise ReviewError('pr_context.action is not a reviewable pull_request action')
    if not is_sha(pr['head_sha']) or not is_sha(pr['base_sha']):
        raise ReviewError('pr_context head_sha and base_sha must be 40 lowercase hex characters')
    if pr['head_sha'] == pr['base_sha']:
        raise ReviewError('pr_context head_sha equals base_sha')
    if not is_branch(pr['base_ref']):
        raise ReviewError('pr_context.base_ref is not a safe branch name')
    if not is_sha(review_head_sha_text):
        raise ReviewError('review_head_sha must be exactly 40 lowercase hex characters')
    if review_head_sha_text != pr['head_sha']:
        raise ReviewError('review_head_sha does not equal pr_context.head_sha')
    allowlist = strict_json(allowlist_text, 'repository_allowlist')
    if type(allowlist) is not list or not 1 <= len(allowlist) <= MAX_ALLOWLIST_ENTRIES:
        raise ReviewError('repository_allowlist must be a non-empty JSON list')
    if not all(is_repository(item) for item in allowlist):
        raise ReviewError('repository_allowlist contains an invalid owner/name')
    if len(set(allowlist)) != len(allowlist):
        raise ReviewError('repository_allowlist contains duplicates')
    if repository not in allowlist:
        raise ReviewError('repository ' + repository + ' is not in repository_allowlist')
    return {
        'repository': repository,
        'pr_number': pr['pr_number'],
        'pr_url': expected_url,
        'action': pr['action'],
        'head_sha': pr['head_sha'],
        'base_sha': pr['base_sha'],
        'base_ref': pr['base_ref'],
    }


def github_url(repository):
    '''The only remote this pipeline contacts: the allowlisted base repository.'''
    if not is_repository(repository):
        raise ReviewError('refusing to build a URL for an invalid repository')
    return 'https://github.com/' + repository + '.git'


# ---------------------------------------------------------------------------
# Git execution (argument lists only; never a shell)
# ---------------------------------------------------------------------------


class Git:
    '''Runs git against one bare repository.

    Network commands keep the worker git configuration (its credential helper
    or broker) but disable hooks, submodules and every protocol except the
    allowed one. Local commands run with an isolated configuration: no system
    or global config, no system attributes, no external diff and no textconv.
    The working directory of every git process is the trusted bare repository.
    '''

    def __init__(self, repo_dir, allowed_protocol='https', timeout=900):
        self.repo_dir = os.path.abspath(repo_dir)
        self.allowed_protocol = allowed_protocol
        self.timeout = timeout

    @staticmethod
    def _base_env():
        env = dict(os.environ)
        for name in REDIRECTING_GIT_ENV:
            env.pop(name, None)
        env['GIT_TERMINAL_PROMPT'] = '0'
        env['GIT_PAGER'] = 'cat'
        env['PAGER'] = 'cat'
        env['GIT_OPTIONAL_LOCKS'] = '0'
        return env

    @classmethod
    def isolated_env(cls):
        env = {k: v for k, v in cls._base_env().items() if not k.startswith('GIT_CONFIG')}
        env['GIT_CONFIG_NOSYSTEM'] = '1'
        env['GIT_CONFIG_GLOBAL'] = os.devnull
        env['GIT_ATTR_NOSYSTEM'] = '1'
        return env

    def _safety_config(self):
        return [
            '-c', 'core.hooksPath=' + os.devnull,
            '-c', 'core.fsmonitor=false',
            '-c', 'core.attributesFile=' + os.devnull,
            '-c', 'core.quotePath=false',
            '-c', 'protocol.allow=never',
            '-c', 'protocol.' + self.allowed_protocol + '.allow=always',
            '-c', 'submodule.recurse=false',
            '-c', 'fetch.recurseSubmodules=false',
            '-c', 'credential.interactive=never',
        ]

    def run(self, args, network=False, ok_codes=(0,)):
        cmd = ['git', '--git-dir=' + self.repo_dir] + self._safety_config() + list(args)
        env = self._base_env() if network else self.isolated_env()
        try:
            proc = subprocess.run(
                cmd,
                cwd=self.repo_dir,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                env=env,
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise ReviewError('git ' + args[0] + ' timed out') from None
        except OSError as exc:
            raise ReviewError('git could not be executed: ' + type(exc).__name__) from None
        if proc.returncode not in ok_codes:
            detail = proc.stderr.decode('utf-8', 'replace').strip().splitlines()
            tail = detail[-1][:300] if detail else ''
            raise ReviewError('git ' + args[0] + ' failed with exit ' + str(proc.returncode) + ': ' + tail)
        return proc.returncode, proc.stdout


def init_bare_repo(repo_dir, work_dir):
    env = Git.isolated_env()
    try:
        proc = subprocess.run(
            ['git', 'init', '--quiet', '--bare', '--template=', repo_dir],
            cwd=work_dir, stdin=subprocess.DEVNULL, capture_output=True, env=env, timeout=120, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise ReviewError('git init could not be executed') from None
    if proc.returncode != 0:
        raise ReviewError('git init failed')


def _ref_listing(out):
    refs = {}
    for line in out.decode('utf-8', 'strict').splitlines():
        if line:
            sha, _, ref = line.partition(TAB)
            refs[ref] = sha
    return refs


def fetch_and_verify(git, identity, url):
    '''Verify the PR binding remotely, fetch exact commits, verify locally.'''
    head = identity['head_sha']
    base = identity['base_sha']
    base_ref = 'refs/heads/' + identity['base_ref']
    pull_ref = 'refs/pull/' + str(identity['pr_number']) + '/head'

    _, out = git.run(['ls-remote', url, pull_ref], network=True)
    if _ref_listing(out).get(pull_ref) != head:
        raise ReviewError('remote ' + pull_ref + ' does not equal the expected head (moved, closed or wrong pull request)')
    _, out = git.run(['ls-remote', '--heads', url], network=True)
    branch_tips = _ref_listing(out)
    if head not in branch_tips.values():
        raise ReviewError('the head commit is not the tip of any branch in the base repository (fork or moved branch)')
    if base_ref not in branch_tips:
        raise ReviewError('base branch ' + identity['base_ref'] + ' does not exist in the base repository')

    git.run([
        'fetch', '--quiet', '--no-tags', '--no-recurse-submodules', '--no-write-fetch-head',
        url,
        '+' + head + ':refs/review/head',
        '+' + base + ':refs/review/base',
        '+' + base_ref + ':refs/review/base-ref',
    ], network=True)

    verify_commits(git, head, base)
    code, _ = git.run(['merge-base', '--is-ancestor', base, 'refs/review/base-ref'], ok_codes=(0, 1))
    if code != 0:
        raise ReviewError('base_sha is not in the history of ' + identity['base_ref'])
    _, out = git.run(['merge-base', base, head])
    merge_base = out.decode('ascii', 'strict').strip()
    if not is_sha(merge_base):
        raise ReviewError('could not determine a single merge base')
    return merge_base


def verify_commits(git, head, base):
    for ref, expected in (('refs/review/head', head), ('refs/review/base', base)):
        _, out = git.run(['rev-parse', '--verify', '--quiet', ref + '^{commit}'])
        actual = out.decode('ascii', 'strict').strip()
        if actual != expected:
            raise ReviewError('retained ' + ref + ' is ' + repr(actual) + ', expected ' + expected)


# ---------------------------------------------------------------------------
# Tree access and evidence text
# ---------------------------------------------------------------------------


def _decode_text(data, what):
    if NUL in data:
        raise ReviewError(what + ' is binary')
    try:
        return data.decode('utf-8', 'strict')
    except UnicodeDecodeError:
        raise ReviewError(what + ' is not valid UTF-8') from None


def _plain_path(raw, what):
    '''Decode a path, refusing anything that cannot be shown unambiguously.'''
    try:
        path = raw.decode('utf-8', 'strict')
    except UnicodeDecodeError:
        raise ReviewError(what + ' contains a path that is not valid UTF-8') from None
    return safe_repo_path(path, what)


def safe_repo_path(path, what):
    '''One safe repository-relative path rule for the inventory, the diff and requests.

    A path is refused when it is empty or overlong, contains a control
    character, a backslash or the transport dollar character, is absolute, or
    has an empty, dot or dot-dot component. Paths are only ever compared by
    exact membership in a frozen tree, never joined to a file system path.
    '''
    if type(path) is not str or not path or len(path) > MAX_PATH_CHARS:
        raise ReviewError(what + ' contains an empty or overlong path')
    if any(ord(c) < 32 or ord(c) == 127 for c in path):
        raise ReviewError(what + ' contains a path with control characters')
    if FULLWIDTH_DOLLAR in path:
        raise ReviewError(what + ' contains a path with the transport dollar character')
    if BACKSLASH in path or path.startswith('/'):
        raise ReviewError(what + ' contains an unsafe path (backslash or absolute): ' + repr(path)[:200])
    if any(part in ('', '.', '..') for part in path.split('/')):
        raise ReviewError(what + ' contains an unsafe path (empty, dot or dot-dot component): ' + repr(path)[:200])
    return path


def list_tree(git, commit):
    '''Map path to (mode, object type, object id, size or None) for a commit.

    An unsafe or unrepresentable path anywhere in the tree fails the review
    closed: the inventory must be complete, never silently incomplete.
    '''
    _, out = git.run(['ls-tree', '-r', '-z', '--long', '--full-tree', commit])
    entries = {}
    for record in out.split(NUL):
        if not record:
            continue
        meta, _, raw_path = record.partition(TAB.encode('ascii'))
        fields = meta.decode('ascii', 'strict').split()
        if len(fields) != 4:
            raise ReviewError('unexpected ls-tree output')
        mode, kind, oid, size = fields
        path = _plain_path(raw_path, 'the file inventory')
        if len(entries) >= MAX_INVENTORY_ENTRIES:
            raise ReviewError('the tree has more than ' + str(MAX_INVENTORY_ENTRIES) + ' entries')
        entries[path] = (mode, kind, oid, int(size) if size.isdigit() else None)
    return entries


def changed_files(git, merge_base, head):
    _, out = git.run(['diff', '--raw', '-z', '--no-renames', '--no-ext-diff', '--no-textconv', '--no-abbrev', merge_base, head, '--'])
    parts = out.split(NUL)
    changes = []
    index = 0
    while index < len(parts) and parts[index]:
        if index + 1 >= len(parts):
            raise ReviewError('unexpected diff --raw output')
        fields = parts[index].decode('ascii', 'strict').lstrip(':').split()
        if len(fields) != 5:
            raise ReviewError('unexpected diff --raw record')
        path = _plain_path(parts[index + 1], 'the changed file list')
        src_mode, dst_mode, _src, _dst, status = fields
        if status not in ('A', 'M', 'D', 'T'):
            raise ReviewError('unsupported change status ' + status + ' for ' + path)
        for mode in (src_mode, dst_mode):
            if len(mode) != 6 or not set(mode) <= set('01234567'):
                raise ReviewError('unexpected mode for ' + path)
            if mode == SUBMODULE_MODE:
                raise ReviewError('changed path ' + path + ' is a submodule pointer (gitlink); its content cannot be reviewed')
        changes.append({'path': path, 'status': status, 'src_mode': src_mode, 'dst_mode': dst_mode})
        index += 2
    if not changes:
        raise ReviewError('the pull request has no changes relative to its merge base')
    if len(changes) > MAX_CHANGED_FILES:
        raise ReviewError(str(len(changes)) + ' changed files exceed the bound of ' + str(MAX_CHANGED_FILES))
    return changes


def read_blob(git, oid, size, limit, what):
    if size is None or size > limit:
        raise ReviewError(what + ' exceeds ' + str(limit) + ' bytes')
    _, data = git.run(['cat-file', 'blob', oid])
    if len(data) != size:
        raise ReviewError(what + ' content length does not match its object size')
    return data


def numbered(text):
    '''Return text with 1-based line numbers, and the line count.'''
    lines = text.split(NL)
    if lines and lines[-1] == '':
        lines = lines[:-1]
    width = max(4, len(str(len(lines))))
    return NL.join(str(n).rjust(width) + '  ' + line for n, line in enumerate(lines, 1)), len(lines)


def transport_escape(text):
    '''Make untrusted text inert for the engine prompt expander.'''
    return text.replace(DOLLAR, FULLWIDTH_DOLLAR)


def wrap_evidence(nonce, stage_note, body):
    return NL.join([
        DATA_BEGIN + nonce,
        'Transport note: every dollar sign in this data is shown as ' + FULLWIDTH_DOLLAR + ' (U+FF04).',
        stage_note,
        '',
        transport_escape(body),
        DATA_END + nonce,
    ]) + NL


STAGE_NOTES = {
    STAGE_SELECT1: 'Retrieval stage: initial evidence. A first file selection round follows.',
    STAGE_SELECT2: 'Retrieval stage: initial evidence plus the files selected in round 1. A second file selection round follows.',
    STAGE_REVIEW: 'Retrieval stage: complete evidence (initial evidence plus rounds 1 and 2). No further files can be requested.',
}


def _base_record(path, side, entry, lines, round_number, reason):
    mode, _kind, oid, size = entry
    return {'path': path, 'side': side, 'mode': mode, 'oid': oid, 'size': size,
            'lines': lines, 'round': round_number, 'reason': reason}


def _changed_version(git, path, side, entry, status):
    '''Read one side of a changed file in full. Returns (section, record).'''
    mode, kind, oid, size = entry
    where = 'HEAD version' if side == 'head' else 'BASE version at the merge base (cite as ' + path + '@base:LINE)'
    title = '--- CHANGED FILE ' + path + ' (status ' + status + ', ' + where
    if mode == SUBMODULE_MODE:
        raise ReviewError('changed path ' + path + ' is a submodule pointer (gitlink); its content cannot be reviewed')
    if kind != 'blob' or (mode not in REGULAR_MODES and mode != SYMLINK_MODE):
        raise ReviewError('changed path ' + path + ' has unsupported mode ' + mode)
    what = 'changed file ' + path + ' (' + side + ')'
    text = _decode_text(read_blob(git, oid, size, MAX_FILE_BYTES, what), what)
    body, count = numbered(text)
    label = 'symlink target text, not followed' if mode == SYMLINK_MODE else 'mode ' + mode
    return title + ', ' + label + ', ' + str(count) + ' lines) ---' + NL + body, _base_record(path, side, entry, count, 0, 'changed file')


def inventory_text(head_tree, base_tree):
    '''Complete union of both trees: side, mode, object id, size and path.'''
    lines = []
    for path in sorted(set(head_tree) | set(base_tree)):
        head_entry = head_tree.get(path)
        base_entry = base_tree.get(path)
        if head_entry and base_entry and head_entry[0] == base_entry[0] and head_entry[2] == base_entry[2]:
            sides = (('both', head_entry),)
        else:
            sides = tuple(item for item in (('head', head_entry), ('base', base_entry)) if item[1])
        for side, entry in sides:
            size = '-' if entry[3] is None else str(entry[3])
            lines.append(side + ' ' + entry[0] + ' ' + entry[2] + ' ' + size + ' ' + path)
    text = NL.join(lines)
    if len(text.encode('utf-8')) > MAX_INVENTORY_BYTES:
        raise ReviewError('the file inventory exceeds ' + str(MAX_INVENTORY_BYTES) + ' bytes')
    return text, len(lines)


def build_base_body(identity, merge_base, git):
    '''The initial evidence body, the changed file metadata and the included records.'''
    head = identity['head_sha']
    changes = changed_files(git, merge_base, head)
    head_tree = list_tree(git, head)
    base_tree = list_tree(git, merge_base)

    sections = []
    included = []
    for change in changes:
        path = change['path']
        status = change['status']
        for side, tree, wanted in (('base', base_tree, status != 'A'), ('head', head_tree, status != 'D')):
            if not wanted:
                continue
            if path not in tree:
                raise ReviewError('changed path ' + path + ' is missing from the ' + side + ' tree')
            section, record = _changed_version(git, path, side, tree[path], status)
            sections.append(section)
            included.append(record)

    _, diff_bytes = git.run([
        'diff', '--no-ext-diff', '--no-textconv', '--no-renames', '--no-color',
        '--full-index', '--unified=5', merge_base, head, '--',
    ])
    if len(diff_bytes) > MAX_DIFF_BYTES:
        raise ReviewError('the diff exceeds ' + str(MAX_DIFF_BYTES) + ' bytes')
    diff_text = _decode_text(diff_bytes, 'the diff')
    inventory, inventory_count = inventory_text(head_tree, base_tree)

    header = [
        'Repository: ' + identity['repository'],
        'Pull request: #' + str(identity['pr_number']) + ' ' + identity['pr_url'],
        'Event action: ' + identity['action'],
        'Head commit (review this exact commit): ' + head,
        'Base commit: ' + identity['base_sha'] + ' on branch ' + identity['base_ref'],
        'Merge base used for the diff: ' + merge_base,
        '',
        'Changed files (' + str(len(changes)) + '):',
    ]
    header.extend('  ' + c['status'] + ' ' + c['path'] for c in changes)
    body = (
        NL.join(header) + NL + NL
        + '== Unified diff (merge base to head) ==' + NL + diff_text + NL
        + '== Complete changed files: the full HEAD version of every added, modified or type-changed file and the full BASE version (at the merge base) of every deleted, modified or type-changed file. Line numbers are the line numbers of that version. ==' + NL
        + (NL + NL).join(sections) + NL + NL
        + '== Complete file inventory: every file at the merge base and at the head, one per line as: side (head, base, or both when identical at both commits), mode, object id, size in bytes (- when not a blob), path. Contents of files that are not listed under changed files or selected files below are NOT shown. ==' + NL
        + inventory + NL
    )
    changed_meta = [dict(c) for c in changes]
    return body, changed_meta, included, inventory_count


# ---------------------------------------------------------------------------
# Work directory and private files
# ---------------------------------------------------------------------------


def check_work_dir(work_dir):
    '''The work directory must be a private, non-symlink directory we own.'''
    try:
        info = os.lstat(work_dir)
    except FileNotFoundError:
        raise ReviewError('the work directory is missing') from None
    except OSError as exc:
        raise ReviewError('the work directory cannot be inspected: ' + type(exc).__name__) from None
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise ReviewError('work directory path exists and is not a directory')
    if info.st_uid != os.geteuid():
        raise ReviewError('the work directory is not owned by the current user')
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise ReviewError('the work directory is not private')


def reset_work_dir(work_dir):
    try:
        info = os.lstat(work_dir)
    except FileNotFoundError:
        info = None
    if info is not None:
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ReviewError('work directory path exists and is not a directory')
        if info.st_uid != os.geteuid():
            raise ReviewError('the existing work directory is not owned by the current user')
        shutil.rmtree(work_dir)
    try:
        os.mkdir(work_dir, 0o700)
    except OSError as exc:
        raise ReviewError('the work directory cannot be created: ' + type(exc).__name__) from None
    check_work_dir(work_dir)


def remove_stale_report(output_dir):
    path = os.path.join(output_dir, OUTPUT_NAME)
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return
    if stat.S_ISDIR(info.st_mode):
        raise ReviewError('report path is a directory')
    os.unlink(path)


def write_private(path, data):
    flags = os.O_WRONLY + os.O_CREAT + os.O_EXCL + getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, 'wb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def read_regular(path, limit, what):
    try:
        fd = os.open(path, os.O_RDONLY + getattr(os, 'O_NOFOLLOW', 0))
    except OSError:
        raise ReviewError(what + ' is missing') from None
    with os.fdopen(fd, 'rb') as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ReviewError(what + ' is not a regular file')
        if info.st_uid != os.geteuid():
            raise ReviewError(what + ' is not owned by the current user')
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise ReviewError(what + ' exceeds ' + str(limit) + ' bytes')
    return data


def write_part(work_dir, name, text):
    '''Store one immutable evidence part and return its manifest entry.'''
    data = text.encode('utf-8')
    write_private(os.path.join(work_dir, name), data)
    return {'name': name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def read_part(work_dir, part):
    data = read_regular(os.path.join(work_dir, part['name']), MAX_EVIDENCE_BYTES, 'evidence part ' + part['name'])
    if hashlib.sha256(data).hexdigest() != part['sha256'] or len(data) != part['bytes']:
        raise ReviewError('evidence part ' + part['name'] + ' does not match its recorded digest')
    return data.decode('utf-8', 'strict')


def save_manifest(work_dir, manifest):
    '''Atomically replace the manifest.'''
    check_work_dir(work_dir)
    final_path = os.path.join(work_dir, MANIFEST_NAME)
    temp_path = os.path.join(work_dir, MANIFEST_NAME + '.tmp')
    if os.path.lexists(temp_path):
        os.unlink(temp_path)
    write_private(temp_path, json.dumps(manifest, sort_keys=True).encode('utf-8'))
    os.replace(temp_path, final_path)


def load_manifest(work_dir):
    check_work_dir(work_dir)
    data = read_regular(os.path.join(work_dir, MANIFEST_NAME), MAX_MANIFEST_BYTES, 'collection manifest')
    try:
        text = data.decode('utf-8', 'strict')
    except UnicodeDecodeError:
        raise ReviewError('collection manifest is not UTF-8') from None
    manifest = strict_json(text, 'collection manifest', max_bytes=MAX_MANIFEST_BYTES)
    if type(manifest) is not dict or manifest.get('kind') != MANIFEST_KIND or manifest.get('version') != MANIFEST_VERSION:
        raise ReviewError('collection manifest is not a pr-review-readonly manifest')
    for key in ('head_sha', 'base_sha', 'merge_base'):
        if not is_sha(manifest.get(key)):
            raise ReviewError('collection manifest ' + key + ' is invalid')
    if not is_repository(manifest.get('repository')) or not is_pr_number(manifest.get('pr_number')):
        raise ReviewError('collection manifest identity is invalid')
    if manifest.get('stage') not in STAGES:
        raise ReviewError('collection manifest stage is invalid')
    if not is_nonce(manifest.get('nonce')):
        raise ReviewError('collection manifest nonce is invalid')
    if type(manifest.get('included')) is not list or type(manifest.get('parts')) is not list:
        raise ReviewError('collection manifest records are invalid')
    return manifest


def checked_evidence(evidence, nonce, what):
    if len(evidence.encode('utf-8')) > MAX_EVIDENCE_BYTES:
        raise ReviewError(what + ' exceeds ' + str(MAX_EVIDENCE_BYTES) + ' bytes')
    if evidence.count(nonce) != 2:
        raise ReviewError('evidence delimiter collision')
    return evidence


def new_nonce():
    return secrets.token_hex(16)


# ---------------------------------------------------------------------------
# collect
# ---------------------------------------------------------------------------


def collect(pr_context_text, review_head_sha_text, allowlist_text, *, work_dir=None,
            output_dir=OUTPUT_DIR, remote_url=github_url, allowed_protocol='https'):
    '''Validate inputs, fetch exact objects and return the engine JSON text.'''
    remove_stale_report(output_dir)
    identity = parse_inputs(pr_context_text, review_head_sha_text, allowlist_text)
    work_dir = work_dir or WORK_DIR
    reset_work_dir(work_dir)
    repo_dir = os.path.join(work_dir, 'repo.git')
    init_bare_repo(repo_dir, work_dir)
    git = Git(repo_dir, allowed_protocol=allowed_protocol)
    merge_base = fetch_and_verify(git, identity, remote_url(identity['repository']))
    nonce = new_nonce()
    body, changed_meta, included, inventory_count = build_base_body(identity, merge_base, git)
    evidence = checked_evidence(
        wrap_evidence(nonce, STAGE_NOTES[STAGE_SELECT1], body), nonce,
        'required evidence (diff, complete changed files and file inventory)')
    part = write_part(work_dir, 'part-base.txt', body)
    manifest = dict(identity)
    manifest.update({
        'kind': MANIFEST_KIND,
        'version': MANIFEST_VERSION,
        'stage': STAGE_SELECT1,
        'nonce': nonce,
        'merge_base': merge_base,
        'changed_files': changed_meta,
        'inventory_entries': inventory_count,
        'included': included,
        'parts': [part],
    })
    save_manifest(work_dir, manifest)
    return json.dumps({EVIDENCE_KEYS[1]: evidence, SELECT1_KEY: ''})


# ---------------------------------------------------------------------------
# expand
# ---------------------------------------------------------------------------


def parse_selection(text, round_number, nonce):
    '''Strictly validate one file selection answer. Returns (path, side, reason) tuples.'''
    obj = strict_json(text, 'file selection response', max_bytes=MAX_SELECTION_BYTES)
    if type(obj) is not dict or set(obj) != {'version', 'round', 'nonce', 'requests'}:
        raise ReviewError('file selection must be a JSON object with exactly version, round, nonce and requests')
    if type(obj['version']) is not int or obj['version'] != 1:
        raise ReviewError('file selection version must be 1')
    if type(obj['round']) is not int or obj['round'] != round_number:
        raise ReviewError('file selection round must be ' + str(round_number))
    if obj['nonce'] != nonce:
        raise ReviewError('file selection nonce does not match the current evidence (stale or inherited answer)')
    requests = obj['requests']
    if type(requests) is not list:
        raise ReviewError('file selection requests must be a list')
    if len(requests) > MAX_REQUESTS:
        raise ReviewError('file selection has more than ' + str(MAX_REQUESTS) + ' requests')
    result = []
    seen = set()
    for item in requests:
        if type(item) is not dict or set(item) != {'path', 'side', 'reason'}:
            raise ReviewError('each file request must have exactly path, side and reason')
        path, side, reason = item['path'], item['side'], item['reason']
        if type(path) is not str:
            raise ReviewError('a requested path is missing')
        try:
            path.encode('utf-8')
        except UnicodeEncodeError:
            raise ReviewError('a requested path is not valid UTF-8 text') from None
        path = safe_repo_path(path.replace(FULLWIDTH_DOLLAR, DOLLAR), 'the file selection')
        if side not in ('head', 'base'):
            raise ReviewError('a requested side must be head or base')
        if type(reason) is not str or not reason.strip() or len(reason) > MAX_REASON_CHARS:
            raise ReviewError('a request reason must be a non-empty string of at most ' + str(MAX_REASON_CHARS) + ' characters')
        try:
            reason.encode('utf-8')
        except UnicodeEncodeError:
            raise ReviewError('a request reason is not valid UTF-8 text') from None
        if any(ord(c) < 32 or ord(c) == 127 for c in reason):
            raise ReviewError('a request reason contains control characters')
        if (path, side) in seen:
            raise ReviewError('a file is requested twice in one round')
        seen.add((path, side))
        result.append((path, side, reason.strip()))
    return result


def read_selected(git, path, side, entry):
    '''Read one requested file by its exact frozen object id. Returns (text, lines).'''
    mode, kind, oid, size = entry
    if kind != 'blob' or mode not in REGULAR_MODES:
        raise ReviewError('requested ' + side + ' path ' + path + ' is not a regular file (symlink, submodule or other mode ' + mode + ')')
    what = 'requested ' + side + ' file ' + path
    text = _decode_text(read_blob(git, oid, size, MAX_SELECTED_FILE_BYTES, what), what)
    body, count = numbered(text)
    return body, count


def expand(round_number, environ, *, work_dir=None, output_dir=OUTPUT_DIR):
    '''Apply one validated selection round and return the engine JSON text.'''
    if round_number not in (1, 2):
        raise ReviewError('unknown selection round')
    remove_stale_report(output_dir)
    work_dir = work_dir or WORK_DIR
    manifest = load_manifest(work_dir)
    stage = STAGE_SELECT1 if round_number == 1 else STAGE_SELECT2
    if manifest['stage'] != stage:
        raise ReviewError('expand' + str(round_number) + ' requires stage ' + stage + ', found ' + manifest['stage'])
    env_name = SELECT1_ENV if round_number == 1 else SELECT2_ENV
    requests = parse_selection(environ.get(env_name), round_number, manifest['nonce'])

    git = Git(os.path.join(work_dir, 'repo.git'))
    verify_commits(git, manifest['head_sha'], manifest['base_sha'])
    _, out = git.run(['rev-parse', '--verify', '--quiet', manifest['merge_base'] + '^{commit}'])
    if out.decode('ascii', 'strict').strip() != manifest['merge_base']:
        raise ReviewError('the retained merge base does not match the manifest')
    trees = {'head': list_tree(git, manifest['head_sha']), 'base': list_tree(git, manifest['merge_base'])}

    included_keys = {(item['path'], item['side']) for item in manifest['included']}
    sections = []
    records = []
    for path, side, reason in requests:
        entry = trees[side].get(path)
        if entry is None:
            raise ReviewError('requested ' + side + ' path ' + repr(path)[:200] + ' does not exist as a file in the frozen tree')
        if (path, side) in included_keys:
            continue
        body, count = read_selected(git, path, side, entry)
        record = _base_record(path, side, entry, count, round_number, reason)
        records.append(record)
        note = '; line numbers are merge base line numbers, cite as ' + path + '@base:LINE' if side == 'base' else ''
        sections.append(
            '--- SELECTED FILE ' + path + ' (side ' + side + ', round ' + str(round_number) + ', mode ' + entry[0]
            + ', ' + str(count) + ' lines, object ' + entry[2] + note + ') ---' + NL
            + 'Reason requested: ' + reason + NL + body)
    text = '== Files selected in round ' + str(round_number) + ' (' + str(len(records)) + ' new) ==' + NL
    if sections:
        text += (NL + NL).join(sections) + NL
    text += NL

    next_stage = STAGE_SELECT2 if round_number == 1 else STAGE_REVIEW
    nonce = new_nonce()
    updated = dict(manifest)
    body = ''.join(read_part(work_dir, part) for part in manifest['parts']) + text
    evidence = checked_evidence(wrap_evidence(nonce, STAGE_NOTES[next_stage], body), nonce, 'the evidence with the selected files')
    part = write_part(work_dir, 'part-round' + str(round_number) + '.txt', text)
    updated.update({
        'stage': next_stage,
        'nonce': nonce,
        'included': manifest['included'] + records,
        'parts': list(manifest['parts']) + [part],
    })
    save_manifest(work_dir, updated)
    next_key = SELECT2_KEY if round_number == 1 else FINAL_KEY
    return json.dumps({EVIDENCE_KEYS[round_number + 1]: evidence, next_key: ''})


# ---------------------------------------------------------------------------
# finalize
# ---------------------------------------------------------------------------


def _clean_text(value, name, limit, single_line=False):
    if type(value) is not str:
        raise ReviewError('model field ' + name + ' is missing')
    value = value.strip()
    if not value:
        raise ReviewError('model field ' + name + ' is empty')
    if len(value) > limit:
        raise ReviewError('model field ' + name + ' exceeds ' + str(limit) + ' characters')
    try:
        value.encode('utf-8')
    except UnicodeEncodeError:
        raise ReviewError('model field ' + name + ' is not valid UTF-8 text') from None
    allowed_controls = () if single_line else (NL, TAB)
    for c in value:
        if (ord(c) < 32 and c not in allowed_controls) or ord(c) == 127:
            raise ReviewError('model field ' + name + ' contains control characters')
    return value


def parse_final(text, manifest):
    '''Strictly validate the final answer and return its fields.'''
    obj = strict_json(text, 'final review response', max_bytes=MAX_FINAL_BYTES)
    keys = {'version', 'nonce', 'evaluated_head_sha', 'context', 'context_gaps', 'verdict', 'title', 'summary', 'review'}
    if type(obj) is not dict or set(obj) != keys:
        raise ReviewError('final review must be a JSON object with exactly ' + ', '.join(sorted(keys)))
    if type(obj['version']) is not int or obj['version'] != 1:
        raise ReviewError('final review version must be 1')
    if obj['nonce'] != manifest['nonce']:
        raise ReviewError('final review nonce does not match the current evidence (stale or inherited answer)')
    if obj['context'] not in (CONTEXT_SUFFICIENT, CONTEXT_INCOMPLETE):
        raise ReviewError('final review context must be SUFFICIENT or INCOMPLETE')
    gaps = obj['context_gaps']
    if type(gaps) is not list or len(gaps) > MAX_CONTEXT_GAPS or not all(type(g) is str for g in gaps):
        raise ReviewError('final review context_gaps must be a short list of strings')
    if obj['context'] == CONTEXT_INCOMPLETE or gaps:
        first = ''.join(c if 32 <= ord(c) != 127 else ' ' for c in (gaps[0] if gaps else ''))[:MAX_GAP_CHARS]
        raise ReviewError('the reviewer reported that the available context was not sufficient: ' + first)
    evaluated = _clean_text(obj['evaluated_head_sha'], 'evaluated_head_sha', 64, single_line=True)
    if evaluated != manifest['head_sha']:
        raise ReviewError('the model evaluated head ' + repr(evaluated) + ', not the collected head ' + manifest['head_sha'])
    verdict = _clean_text(obj['verdict'], 'verdict', 32, single_line=True)
    if verdict not in VERDICT_CONCLUSIONS:
        raise ReviewError('verdict must be PASS or CHANGES_REQUESTED')
    return {
        'verdict': verdict,
        'title': _clean_text(obj['title'], 'title', MAX_MODEL_TITLE, single_line=True),
        'summary': _clean_text(obj['summary'], 'summary', MAX_MODEL_SUMMARY),
        'review': _clean_text(obj['review'], 'review', MAX_MODEL_REVIEW),
    }


def _is_heading(line):
    '''An ATX heading: at most three spaces of indent, one to six hashes, a space.'''
    indent = len(line) - len(line.lstrip(' '))
    if indent > 3:
        return False
    body = line[indent:]
    hashes = len(body) - len(body.lstrip('#'))
    return 1 <= hashes <= 6 and body[hashes:hashes + 1] == ' '


def _fence_marker(line):
    '''Return (character, run length, remainder) for a code fence line, else None.'''
    indent = len(line) - len(line.lstrip(' '))
    if indent > 3:
        return None
    body = line[indent:]
    char = body[:1]
    if char not in ('`', '~'):
        return None
    run = len(body) - len(body.lstrip(char))
    rest = body[run:]
    if run < 3 or (char == '`' and '`' in rest):
        return None
    return char, run, rest


def heading_lines(lines):
    '''Return (index, text) of every heading outside a standard code fence.

    Backtick and tilde fences follow the usual rule: a closing fence uses the
    same character, is at least as long as the opener and carries nothing
    else. An unclosed fence is ambiguous and refused.
    '''
    fence = None
    found = []
    for index, line in enumerate(lines):
        marker = _fence_marker(line)
        if fence is not None:
            if marker and marker[0] == fence[0] and marker[1] >= fence[1] and not marker[2].strip():
                fence = None
            continue
        if marker:
            fence = marker
            continue
        if _is_heading(line):
            found.append((index, line.strip()))
    if fence is not None:
        raise ReviewError('the model review has an unclosed code fence')
    return found


VERDICT_DECORATIONS = frozenset('*_`~#>|[]()')
# Underscores are removed as markdown decoration before matching, so the
# changes-requested token appears without its underscore.
VERDICT_TOKENS = ('pass', 'changesrequested', 'changes requested')


def _plain_for_verdict(line):
    '''Casefolded line text with markdown and HTML decoration and invisible characters removed.'''
    text = unicodedata.normalize('NFKC', line)
    while '<' in text and '>' in text[text.index('<'):]:
        start = text.index('<')
        text = text[:start] + ' ' + text[text.index('>', start) + 1:]
    text = ''.join(c for c in text if c not in VERDICT_DECORATIONS and unicodedata.category(c) != 'Cf')
    return ' '.join(text.split()).casefold().lstrip('-+*.0123456789) ' + chr(8226))


def looks_like_verdict_line(line):
    '''True for any decorated variant of a VERDICT line, which only the pipeline may write.'''
    text = _plain_for_verdict(line)
    at = text.find('verdict')
    while at >= 0:
        rest = text[at + 7:].lstrip()
        sep = rest[:1]
        after = rest[1:].lstrip() if sep in (':', '=', '-', chr(8211), chr(8212)) else rest
        has_token = after.startswith(VERDICT_TOKENS)
        if at == 0 and (sep in (':', '=') or has_token):
            return True
        if at > 0 and has_token and sep in (':', '=', '-', chr(8211), chr(8212)):
            return True
        at = text.find('verdict', at + 1)
    return False


def _digits(text):
    result = ''
    for c in text:
        if c.isascii() and c.isdigit():
            result += c
        else:
            break
    return result


def citations(text, known_head, known_base):
    '''Return (label, first, last, limit) for every path:LINE or path@base:LINE citation.

    A head citation of a path that exists only at the base is refused with
    guidance, as is a base citation of a path that does not exist there.
    '''
    found = []
    for path in sorted(set(known_head) | set(known_base), key=len, reverse=True):
        for side, token, known in (('head', path + ':', known_head), ('base', path + '@base:', known_base)):
            start = 0
            while True:
                at = text.find(token, start)
                if at < 0:
                    break
                start = at + 1
                if at > 0 and text[at - 1] not in ' `([*_' + TAB:
                    continue
                rest = text[at + len(token):]
                digits = _digits(rest)
                if not digits:
                    continue
                if path not in known:
                    if side == 'head':
                        raise ReviewError('a required change cites ' + path + ' at the head but it exists only at the base; cite it as ' + path + '@base:LINE')
                    raise ReviewError('a required change cites ' + path + '@base but no base version was provided')
                first = last = int(digits)
                after = rest[len(digits):]
                if after.startswith('-') and _digits(after[1:]):
                    last = int(_digits(after[1:]))
                found.append((path + ('@base' if side == 'base' else ''), first, last, known[path]))
    return found


def _bullet_text(stripped):
    if stripped.startswith(('- ', '* ')):
        return stripped[2:].strip()
    number = _digits(stripped)
    if number and stripped[len(number):].startswith(('. ', ') ')):
        return stripped[len(number) + 2:].strip()
    return None


def known_lines(manifest):
    known_head = {}
    known_base = {}
    for item in manifest['included']:
        if item.get('lines') is None:
            continue
        (known_head if item['side'] == 'head' else known_base)[item['path']] = item['lines']
    return known_head, known_base


def check_review_structure(review, verdict, manifest):
    '''Deterministic structural checks of the model review markdown.'''
    lines = review.split(NL)
    for line in lines:
        if looks_like_verdict_line(line):
            raise ReviewError('the model review must not contain its own VERDICT line')
    headings = heading_lines(lines)
    expected = ['### ' + name for name in REVIEW_HEADINGS]
    if [title for _, title in headings] != expected:
        raise ReviewError('the model review must contain exactly the headings ' + ', '.join(expected) + ' once each, in that order, and no other heading')
    section = [line.strip() for line in lines[headings[-1][0] + 1:] if line.strip()]
    if verdict == 'PASS':
        if section != [NONE_BULLET]:
            raise ReviewError('a PASS review must list exactly one bullet, ' + NONE_BULLET + ', under Required changes')
        return
    known_head, known_base = known_lines(manifest)
    bullets = []
    for line in section:
        bullet = _bullet_text(line)
        if bullet is None:
            raise ReviewError('every line under Required changes must be one bullet')
        if bullet.lower().rstrip('.') in NONE_MARKERS:
            raise ReviewError('a CHANGES_REQUESTED review must not list None as a required change')
        bullets.append(bullet)
    if not bullets:
        raise ReviewError('a CHANGES_REQUESTED review must list at least one required change')
    for bullet in bullets:
        cites = citations(bullet, known_head, known_base)
        if not cites:
            raise ReviewError('a required change lacks a path:line citation of a reviewed file: ' + bullet[:120])
        for label, first, last, limit in cites:
            if first < 1 or last < first or last > limit:
                raise ReviewError('a required change cites ' + label + ':' + str(first) + ' outside the reviewed file')


def validate_report(report):
    '''Strict review-result.json contract, version 1.'''
    if type(report) is not dict:
        raise ReviewError('report must be a JSON object')
    keys = set(report)
    if not REPORT_REQUIRED <= keys or not keys <= set(REPORT_KEYS):
        raise ReviewError('report keys mismatch')
    if type(report['version']) is not int or report['version'] != REPORT_VERSION:
        raise ReviewError('report version must be 1')
    if not is_repository(report['repository']):
        raise ReviewError('report repository is invalid')
    if not is_pr_number(report['pr_number']):
        raise ReviewError('report pr_number is invalid')
    if not is_sha(report['head_sha']):
        raise ReviewError('report head_sha is invalid')
    if report['conclusion'] not in REPORT_CONCLUSIONS:
        raise ReviewError('report conclusion is invalid')
    for key, limit in (('title', MAX_REPORT_TITLE), ('summary', MAX_REPORT_SUMMARY), ('text', MAX_REPORT_TEXT)):
        if key not in report:
            continue
        value = report[key]
        if type(value) is not str or not value or len(value) > limit:
            raise ReviewError('report ' + key + ' must be a non-empty string of at most ' + str(limit) + ' characters')
        try:
            value.encode('utf-8')
        except UnicodeEncodeError:
            raise ReviewError('report ' + key + ' is not valid UTF-8 text') from None
        allowed_controls = () if key == 'title' else (NL, TAB)
        for c in value:
            if (ord(c) < 32 and c not in allowed_controls) or ord(c) == 127:
                raise ReviewError('report ' + key + ' contains control characters')
    if NL in report['title']:
        raise ReviewError('report title must be one line')
    return report


def serialize_report(report):
    validate_report(report)
    ordered = {key: report[key] for key in REPORT_KEYS if key in report}
    data = (json.dumps(ordered, ensure_ascii=False, indent=2) + NL).encode('utf-8')
    if len(data) > MAX_REPORT_BYTES:
        raise ReviewError('report exceeds ' + str(MAX_REPORT_BYTES) + ' bytes')
    return data


def parse_report_bytes(data):
    if len(data) > MAX_REPORT_BYTES:
        raise ReviewError('report exceeds ' + str(MAX_REPORT_BYTES) + ' bytes')
    try:
        text = data.decode('utf-8', 'strict')
    except UnicodeDecodeError:
        raise ReviewError('report is not UTF-8') from None
    return validate_report(strict_json(text, 'report', max_bytes=MAX_REPORT_BYTES))


def build_report(manifest, fields):
    verdict = fields['verdict']
    check_review_structure(fields['review'], verdict, manifest)
    head = manifest['head_sha']
    footer = NL.join([
        '---',
        'Repository: ' + manifest['repository'],
        'Pull request: #' + str(manifest['pr_number']),
        'Reviewed head commit: ' + head,
        'Base commit: ' + manifest['base_sha'] + ' (' + manifest['base_ref'] + '), merge base ' + manifest['merge_base'],
        '',
        'VERDICT: ' + verdict,
        '',
        CAVEAT,
    ])
    return {
        'version': REPORT_VERSION,
        'repository': manifest['repository'],
        'pr_number': manifest['pr_number'],
        'head_sha': head,
        'conclusion': VERDICT_CONCLUSIONS[verdict],
        'title': verdict + ': ' + fields['title'],
        'summary': fields['summary'] + NL + NL + 'Reviewed ' + manifest['repository'] + '#' + str(manifest['pr_number']) + ' at head ' + head + '.',
        'text': fields['review'] + NL + NL + footer,
    }


def finalize(environ, *, work_dir=None, output_dir=OUTPUT_DIR):
    '''Validate the final answer and atomically write the strict report.'''
    remove_stale_report(output_dir)
    work_dir = work_dir or WORK_DIR
    manifest = load_manifest(work_dir)
    if manifest['stage'] != STAGE_REVIEW:
        raise ReviewError('finalize requires stage ' + STAGE_REVIEW + ', found ' + manifest['stage'])
    fields = parse_final(environ.get(FINAL_ENV), manifest)
    report = build_report(manifest, fields)
    data = serialize_report(report)
    if parse_report_bytes(data) != report:
        raise ReviewError('the serialized report does not round-trip')
    done = dict(manifest)
    done['stage'] = STAGE_FINALIZED
    final_path = os.path.join(output_dir, OUTPUT_NAME)
    temp_path = os.path.join(output_dir, '.' + OUTPUT_NAME + '.' + secrets.token_hex(8) + '.tmp')
    # Publishing is the LAST fallible commitment: everything that can fail
    # (writing, mode, read-back, the finalized manifest) happens first, and
    # the single atomic rename comes last. Any exception, including an
    # infrastructure OSError, removes the temporary file and any report.
    try:
        os.makedirs(output_dir, exist_ok=True)
        write_private(temp_path, data)
        os.chmod(temp_path, 0o644)
        if read_regular(temp_path, MAX_REPORT_BYTES, 'pending report') != data:
            raise ReviewError('the pending report does not match the validated report')
        save_manifest(work_dir, done)
        os.replace(temp_path, final_path)
    except BaseException:
        for leftover in (temp_path, final_path):
            try:
                if os.path.lexists(leftover):
                    os.unlink(leftover)
            except OSError:
                pass
        raise
    shutil.rmtree(os.path.join(work_dir, 'repo.git'), ignore_errors=True)
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

COMMANDS = ('collect', 'expand1', 'expand2', 'finalize')


def main(argv=None, environ=None):
    argv = sys.argv[1:] if argv is None else argv
    environ = os.environ if environ is None else environ
    if len(argv) != 1 or argv[0] not in COMMANDS:
        sys.stderr.write('usage: pr_review_readonly.py (' + ' or '.join(COMMANDS) + ')' + NL)
        return 64
    try:
        if argv[0] == 'collect':
            output = collect(
                environ.get('PR_CONTEXT'),
                environ.get('REVIEW_HEAD_SHA'),
                environ.get('REPOSITORY_ALLOWLIST'),
            )
            sys.stdout.write(output + NL)
        elif argv[0] in ('expand1', 'expand2'):
            sys.stdout.write(expand(int(argv[0][-1]), environ) + NL)
        else:
            # No output after publication: a stdout failure there could
            # otherwise leave a valid report next to a failed run.
            finalize(environ)
    except ReviewError as exc:
        sys.stderr.write('pr-review-readonly refused: ' + str(exc) + NL)
        return 2
    except Exception as exc:  # noqa: BLE001 - an infrastructure failure, never a review
        sys.stderr.write('pr-review-readonly failed: ' + type(exc).__name__ + ': ' + str(exc)[:300] + NL)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
