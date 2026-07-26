import sys
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime

# ===================== 基础数据结构定义 =====================
@dataclass
class FSNode:
    is_dir: bool
    content: str = ""
    mode: int = 0o755
    owner: str = "root"
    children: Optional[Dict[str, "FSNode"]] = None

    def __post_init__(self):
        if self.is_dir and self.children is None:
            self.children = {}

@dataclass
class ProcItem:
    pid: int
    name: str
    status: str

# 用户列表
user_list = {
    "root": {"uid": 0, "home": "/home/root"},
    "guest": {"uid": 1000, "home": "/home/guest"}
}
current_user = "root"
hostname = "unix‑vm"
env_vars:Dict[str,str] = {
    "PATH":"/bin:/usr/bin",
    "USER":"root",
    "HOME":"/home/root",
    "HOSTNAME":"unix‑vm"
}
proc_list:List[ProcItem] = [ProcItem(pid=1,name="init",status="running")]
next_pid = 2

# 构建虚拟目录树
root = FSNode(is_dir=True)
root.children["etc"] = FSNode(is_dir=True)
root.children["etc"]["passwd"] = FSNode(is_dir=False,content="root:x:0:0::/home/root:\nguest:x:1000:1000::/home/guest:\n")
root.children["etc"]["hostname"] = FSNode(is_dir=False,content="unix‑vm\n")
root.children["etc"]["motd"] = FSNode(is_dir=False,content="Mini‑UNIX 0.3 Virtual System\nSingle‑file simulation terminal\nBuild:2026‑07\n")
root.children["bin"] = FSNode(is_dir=True)
root.children["usr"] = FSNode(is_dir=True)
root.children["usr"]["bin"] = FSNode(is_dir=True)
root.children["home"] = FSNode(is_dir=True)
root.children["home"]["root"] = FSNode(is_dir=True)
root.children["home"]["root"]["readme.txt"] = FSNode(is_dir=False,content="Welcome to mini unix shell\nVersion 0.3 build‑2026\nSupport pipe | ,env,ps,kill,wc,head,tail\n")
root.children["home"]["guest"] = FSNode(is_dir=True)

cwd_path: List[str] = ["home", "root"]
history: List[str] = []
profile_counter: Dict[str, int] = {}
SYS_NAME = "mini‑unix"

# ===================== 工具函数 =====================
def get_current_node() -> FSNode:
    node = root
    for seg in cwd_path:
        node = node.children[seg]
    return node

def resolve_path(path_str: str):
    if not path_str:
        return None, None
    absolute = path_str.startswith("/")
    parts = path_str.strip("/").split("/")
    node = root if absolute else get_current_node()
    temp_path = cwd_path.copy()
    for p in parts:
        if p == "" or p == ".":
            continue
        if p == "..":
            if not absolute and len(temp_path) > 0:
                temp_path.pop()
            continue
        if p not in node.children:
            return None, None
        node = node.children[p]
        if not absolute:
            temp_path.append(p)
    return node, temp_path

def split_redirection(args: List[str]):
    out_args = []
    redirect_file = None
    append_mode = False
    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg == ">":
            if idx + 1 < len(args):
                redirect_file = args[idx + 1]
                append_mode = False
            break
        elif arg == ">>":
            if idx + 1 < len(args):
                redirect_file = args[idx + 1]
                append_mode = True
            break
        out_args.append(arg)
        idx += 1
    return out_args, redirect_file, append_mode

def write_to_file(filename: str, text: str, append: bool):
    cur = get_current_node()
    node, _ = resolve_path(filename)
    if node is None:
        cur.children[filename] = FSNode(is_dir=False, content=text,owner=current_user)
    else:
        if node.is_dir:
            print(f"sh: {filename}: Is a directory")
            return
        if append:
            node.content += text
        else:
            node.content = text

def calc_dir_size(node:FSNode)->int:
    size = 0
    if not node.is_dir:
        size = len(node.content)
    else:
        for _,child in node.children.items():
            size += calc_dir_size(child)
    return size

def run_command_pipe(cmdname:str,argv:List[str],stdin_data:str="")->str:
    buffer = []
    def fake_print(*text):
        buffer.append(" ".join(map(str,text)))
    if cmdname == "echo":
        fake_print(" ".join(argv))
    elif cmdname == "pwd":
        fake_print("/" + "/".join(cwd_path))
    elif cmdname == "whoami":
        fake_print(current_user)
    elif cmdname == "date":
        fake_print(datetime.now().strftime("%a %b %d %H:%M:%S %Y"))
    elif cmdname == "hostname":
        fake_print(hostname)
    elif cmdname == "uname":
        if "-a" in argv:
            fake_print(f"{SYS_NAME} 0.3‑virtual x86_64 python‑sim")
        else:
            fake_print(SYS_NAME)
    elif cmdname == "wc":
        source = stdin_data
        if not source and len(argv)>=1:
            n,_=resolve_path(argv[0])
            if n and not n.is_dir:
                source = n.content
        lines = len(source.splitlines())
        words = len(source.split())
        chars = len(source)
        fake_print(f"{lines} {words} {chars}")
    elif cmdname == "head":
        source = stdin_data
        if not source and len(argv)>=1:
            n,_=resolve_path(argv[0])
            if n and not n.is_dir:
                source = n.content
        lines = source.splitlines()[:10]
        fake_print("\n".join(lines))
    elif cmdname == "tail":
        source = stdin_data
        if not source and len(argv)>=1:
            n,_=resolve_path(argv[0])
            if n and not n.is_dir:
                source = n.content
        lines = source.splitlines()[-10:]
        fake_print("\n".join(lines))
    return "\n".join(buffer)+"\n"

# ===================== 内置命令实现 =====================
def cmd_ls(args: List[str]):
    target_node = get_current_node()
    target_args, redir_file, append = split_redirection(args)
    if target_args:
        target_node, _ = resolve_path(target_args[0])
    output = []
    if target_node is None or not target_node.is_dir:
        line = "ls: No such directory"
        if redir_file:
            write_to_file(redir_file, line + "\n", append)
            return
        print(line)
        return
    for name, child in sorted(target_node.children.items()):
        perm = oct(child.mode)[-3:]
        if child.is_dir:
            output.append(f"d{perm} {child.owner:<8} {name}/")
        else:
            output.append(f"-{perm} {child.owner:<8} {name}")
    text = "\n".join(output) + "\n"
    if redir_file:
        write_to_file(redir_file, text, append)
    else:
        for line in output:
            print(line)

def cmd_cd(args: List[str]):
    global cwd_path
    if not args:
        cwd_path = user_list[current_user]["home"].strip("/").split("/")
        return
    dest = args[0]
    if dest == "/":
        cwd_path.clear()
        return
    node, new_path = resolve_path(dest)
    if node is None or not node.is_dir:
        print(f"cd: {dest}: No such directory")
        return
    cwd_path = new_path

def cmd_pwd(args: List[str]):
    argv, redir_file, append = split_redirection(args)
    res = "/" + "/".join(cwd_path) + "\n"
    if redir_file:
        write_to_file(redir_file, res, append)
    else:
        print(res, end="")

def cmd_mkdir(args: List[str]):
    if not args:
        print("mkdir: missing operand")
        return
    cur = get_current_node()
    name = args[0]
    if name in cur.children:
        print(f"mkdir: {name}: File exists")
        return
    cur.children[name] = FSNode(is_dir=True,owner=current_user)

def cmd_touch(args: List[str]):
    if not args:
        print("touch: missing file name")
        return
    cur = get_current_node()
    fname = args[0]
    if fname not in cur.children:
        cur.children[fname] = FSNode(is_dir=False, content="",owner=current_user)

def cmd_cat(args: List[str]):
    argv, redir_file, append = split_redirection(args)
    if not argv:
        print("cat: need filename argument")
        return
    node, _ = resolve_path(argv[0])
    if node is None or node.is_dir:
        print(f"cat: {argv[0]}: No such file")
        return
    if redir_file:
        write_to_file(redir_file, node.content, append)
    else:
        sys.stdout.write(node.content)

def cmd_echo(args: List[str]):
    argv, redir_file, append = split_redirection(args)
    text = " ".join(argv) + "\n"
    if redir_file:
        write_to_file(redir_file, text, append)
    else:
        print(" ".join(argv))

def cmd_rm(args: List[str]):
    if not args:
        print("rm: missing operand")
        return
    cur = get_current_node()
    name = args[0]
    if name not in cur.children:
        print(f"rm: {name}: No such file or directory")
        return
    del cur.children[name]

def cmd_cp(args: List[str]):
    if len(args) < 2:
        print("cp: missing file operand")
        return
    src, _ = resolve_path(args[0])
    if src is None or src.is_dir:
        print(f"cp: cannot copy folder")
        return
    cur = get_current_node()
    dst_name = args[1]
    cur.children[dst_name] = FSNode(is_dir=False, content=src.content,owner=current_user)

def cmd_mv(args: List[str]):
    if len(args) < 2:
        print("mv: missing operand")
        return
    cur = get_current_node()
    src_name = args[0]
    dst_name = args[1]
    if src_name not in cur.children:
        print(f"mv: {src_name} not found")
        return
    cur.children[dst_name] = cur.children[src_name]
    del cur.children[src_name]

def cmd_chmod(args: List[str]):
    if len(args) <2:
        print("chmod: missing operand")
        return
    try:
        mode = int(args[0],8)
    except ValueError:
        print("chmod: invalid mode")
        return
    node,_ = resolve_path(args[1])
    if node is None:
        print(f"chmod: {args[1]} not found")
        return
    node.mode = mode

def cmd_clear(_args: List[str]):
    os.system("cls" if os.name == "nt" else "clear")

def cmd_whoami(args:List[str]):
    argv, redir_file, append = split_redirection(args)
    out = current_user+"\n"
    if redir_file:
        write_to_file(redir_file,out,append)
    else:
        print(current_user)

def cmd_su(args:List[str]):
    global current_user,cwd_path
    if not args:
        print("su: need username")
        return
    uname = args[0]
    if uname not in user_list:
        print(f"su: user {uname} does not exist")
        return
    current_user = uname
    env_vars["USER"] = uname
    env_vars["HOME"] = user_list[uname]["home"]
    hp = user_list[uname]["home"].strip("/").split("/")
    cwd_path = hp

def cmd_uname(args: List[str]):
    argv, redir_file, append = split_redirection(args)
    if "-a" in argv:
        out = f"{SYS_NAME} 0.3‑virtual x86_64 python‑simulated terminal\n"
    else:
        out = SYS_NAME+"\n"
    if redir_file:
        write_to_file(redir_file,out,append)
    else:
        print(out,end="")

def cmd_date(args:List[str]):
    argv, redir_file, append = split_redirection(args)
    out = datetime.now().strftime("%a %b %d %H:%M:%S %Y")+"\n"
    if redir_file:
        write_to_file(redir_file,out,append)
    else:
        print(out,end="")

def cmd_du(args:List[str]):
    argv, redir_file, append = split_redirection(args)
    target = get_current_node()
    if argv:
        target,_ = resolve_path(argv[0])
    size = calc_dir_size(target)
    out = f"{size}\t.\n"
    if redir_file:
        write_to_file(redir_file,out,append)
    else:
        print(f"{size}\t.")

def cmd_sleep(args:List[str]):
    if not args:
        return
    try:
        t = float(args[0])
        time.sleep(t)
    except ValueError:
        print("sleep: invalid number")

def cmd_history(args: List[str]):
    argv, redir_file, append = split_redirection(args)
    buf = []
    for i, item in enumerate(history):
        buf.append(f" {i:3d}  {item}")
    text = "\n".join(buf)+"\n"
    if redir_file:
        write_to_file(redir_file,text,append)
    else:
        for line in buf:
            print(line)

def cmd_profiler(args: List[str]):
    argv, redir_file, append = split_redirection(args)
    buf=["========== Performance Profiler =========="]
    if not profile_counter:
        buf.append("No command executed yet.")
    else:
        for cmd, cnt in sorted(profile_counter.items()):
            buf.append(f"{cmd:<14} run count : {cnt}")
    buf.append("==========================================")
    text = "\n".join(buf)+"\n"
    if redir_file:
        write_to_file(redir_file,text,append)
    else:
        for line in buf:
            print(line)

def cmd_env(args:List[str]):
    argv, redir_file, append = split_redirection(args)
    buf=[]
    for k,v in env_vars.items():
        buf.append(f"{k}={v}")
    text = "\n".join(buf)+"\n"
    if redir_file:
        write_to_file(redir_file,text,append)
    else:
        for line in buf:
            print(line)

def cmd_export(args:List[str]):
    if not args:
        return
    pair = args[0].split("=",1)
    if len(pair)==2:
        env_vars[pair[0]] = pair[1]

def cmd_ps(args:List[str]):
    argv, redir_file, append = split_redirection(args)
    buf=[f"{'PID':<6}{'NAME':<12}{'STATUS'}"]
    for p in proc_list:
        buf.append(f"{p.pid:<6}{p.name:<12}{p.status}")
    text = "\n".join(buf)+"\n"
    if redir_file:
        write_to_file(redir_file,text,append)
    else:
        for line in buf:
            print(line)

def cmd_kill(args:List[str]):
    global proc_list
    if not args:
        print("kill: need pid")
        return
    try:
        pid = int(args[0])
    except ValueError:
        print("kill: invalid pid")
        return
    find = False
    for item in proc_list:
        if item.pid == pid:
            item.status = "terminated"
            find=True
            break
    if not find:
        print(f"kill: pid {pid} not found")

def cmd_hostname(args:List[str]):
    global hostname
    argv, redir_file, append = split_redirection(args)
    if argv:
        hostname = argv[0]
        env_vars["HOSTNAME"] = hostname
    out = hostname+"\n"
    if redir_file:
        write_to_file(redir_file,out,append)
    else:
        print(hostname)

def cmd_wc(args:List[str]):
    argv, redir_file, append = split_redirection(args)
    if not argv:
        print("wc: need filename")
        return
    node,_ = resolve_path(argv[0])
    if node is None or node.is_dir:
        print(f"wc: {args[0]} no such file")
        return
    data = node.content
    lc = len(data.splitlines())
    wc = len(data.split())
    cc = len(data)
    out = f"{lc} {wc} {cc} {argv[0]}\n"
    if redir_file:
        write_to_file(redir_file,out,append)
    else:
        print(f"{lc} {wc} {cc} {argv[0]}")

def cmd_head(args:List[str]):
    argv, redir_file, append = split_redirection(args)
    if not argv:
        print("head: need filename")
        return
    node,_ = resolve_path(argv[0])
    if node is None or node.is_dir:
        print(f"head: {argv[0]} no such file")
        return
    lines = node.content.splitlines()[:10]
    text = "\n".join(lines)+"\n"
    if redir_file:
        write_to_file(redir_file,text,append)
    else:
        print("\n".join(lines))

def cmd_tail(args:List[str]):
    argv, redir_file, append = split_redirection(args)
    if not argv:
        print("tail: need filename")
        return
    node,_ = resolve_path(argv[0])
    if node is None or node.is_dir:
        print(f"tail: {argv[0]} no such file")
        return
    lines = node.content.splitlines()[-10:]
    text = "\n".join(lines)+"\n"
    if redir_file:
        write_to_file(redir_file,text,append)
    else:
        print("\n".join(lines))

def cmd_help(_args: List[str]):
    print("""
Command List:
    ls          list directory
    cd          change directory
    pwd         print work path
    mkdir       create folder
    touch       create empty file
    cat         view file
    echo        print text (> >> redirect)
    rm          delete file
    cp          copy file
    mv          rename/move
    chmod       change permission
    clear       clear screen
    whoami      show current user
    su          switch user(root/guest)
    uname‑a     system info
    date        show time
    du          dir byte size
    sleep N     delay seconds
    hostname    set/show hostname
    env         print environment
    export      set env variable
    ps          list process
    kill        kill process by pid
    wc          count line/word/char
    head        show first 10 lines
    tail        show last 10 lines
    history     command history
    profiler    run‑count statistics
    help        help info
    exit        shutdown
Pipe usage: echo test | wc
""")

cmd_map = {
    "ls": cmd_ls,
    "cd": cmd_cd,
    "pwd": cmd_pwd,
    "mkdir": cmd_mkdir,
    "touch": cmd_touch,
    "cat": cmd_cat,
    "echo": cmd_echo,
    "rm": cmd_rm,
    "cp": cmd_cp,
    "mv": cmd_mv,
    "chmod": cmd_chmod,
    "clear": cmd_clear,
    "whoami": cmd_whoami,
    "su":cmd_su,
    "uname": cmd_uname,
    "date":cmd_date,
    "du":cmd_du,
    "sleep":cmd_sleep,
    "history": cmd_history,
    "profiler": cmd_profiler,
    "env":cmd_env,
    "export":cmd_export,
    "ps":cmd_ps,
    "kill":cmd_kill,
    "hostname":cmd_hostname,
    "wc":cmd_wc,
    "head":cmd_head,
    "tail":cmd_tail,
    "help": cmd_help,
}

# ===================== 主交互循环（支持简单管道 |） =====================
def parse_pipe(line:str)->List[List[str]]:
    pieces = line.split("|")
    cmds = []
    for p in pieces:
        part = p.strip().split()
        if part:
            cmds.append(part)
    return cmds

def main():
    global next_pid
    print("Mini‑UNIX 0.3 (Single‑File Virtual Terminal)")
    print("Type 'help' to list commands, 'exit' to quit\n")
    while True:
        full_path = "/" + "/".join(cwd_path)
        prompt = f"\033[92m{current_user}\033[0m@{hostname}:\033[94m{full_path}\033[0m# "
        try:
            raw = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print("\nSystem halted.")
            break
        line = raw.strip()
        if not line:
            continue
        history.append(line)
        pipe_cmds = parse_pipe(line)
        if len(pipe_cmds)>1:
            buf = ""
            for argv in pipe_cmds:
                cname = argv[0]
                buf = run_command_pipe(cname,argv[1:],buf)
            print(buf,end="")
            continue
        parts = line.split()
        cmd = parts[0]
        argv = parts[1:]
        if cmd == "exit":
            print("System shutdown. Bye.")
            break
        proc_list.append(ProcItem(pid=next_pid,name=cmd,status="running"))
        next_pid +=1
        if cmd in profile_counter:
            profile_counter[cmd] += 1
        else:
            profile_counter[cmd] = 1
        if cmd in cmd_map:
            cmd_map[cmd](argv)
        else:
            print(f"{cmd}: command not found")

if __name__ == "__main__":
    main()