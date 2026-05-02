import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import subprocess
import threading
import json
import os
import sys

CONFIG_FILE = "gost_history.json"

class GostGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Gost 代理控制台 (多规则版)")
        self.root.geometry("700x600")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.process = None
        self.rule_rows = []  # 保存所有转发规则界面的引用
        self.config = self.load_config()

        self.create_widgets()
        self.load_session_to_ui()

    def load_config(self):
        """加载历史配置文件"""
        default_config = {
            "history": {
                "gost_path": [],
                "socks_ip": ["127.0.0.1"],
                "socks_port": ["7890"],
                "local_port": ["6690", "5001"],
                "remote_ip": ["192.168.124.10"],
                "remote_port": ["6690", "5001"]
            },
            "last_session": {
                "gost_path": "",
                "socks_ip": "127.0.0.1",
                "socks_port": "7890",
                "rules": [
                    {"lp": "6690", "rip": "192.168.124.10", "rp": "6690"}
                ]
            }
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved_config = json.load(f)
                    
                    # 兼容旧版本配置文件格式的迁移
                    if "history" not in saved_config:
                        return default_config
                        
                    # 合并配置
                    default_config["history"].update(saved_config.get("history", {}))
                    default_config["last_session"] = saved_config.get("last_session", default_config["last_session"])
            except Exception as e:
                print(f"读取配置文件失败: {e}")
        return default_config

    def save_config(self):
        """保存当前输入并更新历史记录"""
        def update_history(key, value):
            if not value: return
            hist = self.config["history"].get(key, [])
            if value in hist:
                hist.remove(value)
            hist.insert(0, value)
            self.config["history"][key] = hist[:10]  # 最多保留 10 条历史

        # 保存全局设置
        g_path = self.cb_gost_path.get()
        s_ip = self.cb_socks_ip.get()
        s_port = self.cb_socks_port.get()
        
        update_history("gost_path", g_path)
        update_history("socks_ip", s_ip)
        update_history("socks_port", s_port)

        self.config["last_session"]["gost_path"] = g_path
        self.config["last_session"]["socks_ip"] = s_ip
        self.config["last_session"]["socks_port"] = s_port

        # 保存转发规则
        rules_session = []
        for row in self.rule_rows:
            lp = row["lp"].get().strip()
            rip = row["rip"].get().strip()
            rp = row["rp"].get().strip()
            
            if lp or rip or rp:
                rules_session.append({"lp": lp, "rip": rip, "rp": rp})
                update_history("local_port", lp)
                update_history("remote_ip", rip)
                update_history("remote_port", rp)

        self.config["last_session"]["rules"] = rules_session

        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            self.log(f"[系统] 保存配置失败: {e}")

    def create_widgets(self):
        """绘制界面 UI"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ---- 全局参数区域 ----
        global_frame = ttk.LabelFrame(main_frame, text="全局配置", padding="10")
        global_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(global_frame, text="Gost 路径:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.cb_gost_path = ttk.Combobox(global_frame, width=50)
        self.cb_gost_path.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5, columnspan=3)
        btn_browse = ttk.Button(global_frame, text="浏览...", command=self.browse_file)
        btn_browse.grid(row=0, column=4, padx=5, pady=5)

        ttk.Label(global_frame, text="Socks5 IP:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.cb_socks_ip = ttk.Combobox(global_frame, width=15)
        self.cb_socks_ip.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(global_frame, text="Socks5 端口:").grid(row=1, column=2, sticky=tk.E, pady=5)
        self.cb_socks_port = ttk.Combobox(global_frame, width=8)
        self.cb_socks_port.grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)

        global_frame.columnconfigure(1, weight=1)

        # ---- 转发规则区域 ----
        self.rules_frame = ttk.LabelFrame(main_frame, text="端口转发规则 (-L)", padding="10")
        self.rules_frame.pack(fill=tk.X, pady=(0, 10))

        # ---- 操作按钮区域 ----
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.btn_toggle = ttk.Button(btn_frame, text="连  接", command=self.toggle_connection)
        self.btn_toggle.pack(side=tk.LEFT, padx=5)

        btn_clear = ttk.Button(btn_frame, text="清空日志", command=lambda: self.txt_log.delete(1.0, tk.END))
        btn_clear.pack(side=tk.LEFT, padx=5)

        # ---- 日志控制台区域 ----
        log_frame = ttk.LabelFrame(main_frame, text="控制台日志 (实时)", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.txt_log = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, bg="black", fg="lightgreen", font=("Consolas", 10))
        self.txt_log.pack(fill=tk.BOTH, expand=True)

    def add_rule_row(self, lp_val="", rip_val="", rp_val=""):
        """动态添加一行转发规则"""
        row_frame = ttk.Frame(self.rules_frame)
        row_frame.pack(fill=tk.X, pady=2)

        ttk.Label(row_frame, text="本地端口:").pack(side=tk.LEFT, padx=(0, 5))
        cb_lp = ttk.Combobox(row_frame, width=8, values=self.config["history"].get("local_port", []))
        cb_lp.pack(side=tk.LEFT, padx=(0, 15))
        cb_lp.set(lp_val)

        ttk.Label(row_frame, text="远程 IP:").pack(side=tk.LEFT, padx=(0, 5))
        cb_rip = ttk.Combobox(row_frame, width=15, values=self.config["history"].get("remote_ip", []))
        cb_rip.pack(side=tk.LEFT, padx=(0, 15))
        cb_rip.set(rip_val)

        ttk.Label(row_frame, text="远程端口:").pack(side=tk.LEFT, padx=(0, 5))
        cb_rp = ttk.Combobox(row_frame, width=8, values=self.config["history"].get("remote_port", []))
        cb_rp.pack(side=tk.LEFT, padx=(0, 15))
        cb_rp.set(rp_val)

        # 判断是创建 '+' 按钮还是 '-' 按钮
        if len(self.rule_rows) == 0:
            btn = ttk.Button(row_frame, text="+", width=3, command=lambda: self.add_rule_row())
            btn.pack(side=tk.LEFT)
        else:
            btn = ttk.Button(row_frame, text="-", width=3)
            btn.pack(side=tk.LEFT)
            # 绑定删除事件
            rule_dict = {"frame": row_frame, "lp": cb_lp, "rip": cb_rip, "rp": cb_rp}
            btn.config(command=lambda: self.remove_rule_row(rule_dict))

        if len(self.rule_rows) == 0:
            self.rule_rows.append({"frame": row_frame, "lp": cb_lp, "rip": cb_rip, "rp": cb_rp})
        else:
            self.rule_rows.append(rule_dict)

    def remove_rule_row(self, rule_dict):
        """删除指定的规则行"""
        rule_dict["frame"].destroy()
        self.rule_rows.remove(rule_dict)

    def load_session_to_ui(self):
        """将上次关闭时的状态加载到界面上"""
        hist = self.config["history"]
        last = self.config["last_session"]

        self.cb_gost_path['values'] = hist.get("gost_path", [])
        self.cb_gost_path.set(last.get("gost_path", ""))

        self.cb_socks_ip['values'] = hist.get("socks_ip", [])
        self.cb_socks_ip.set(last.get("socks_ip", ""))

        self.cb_socks_port['values'] = hist.get("socks_port", [])
        self.cb_socks_port.set(last.get("socks_port", ""))

        # 加载规则
        rules = last.get("rules", [])
        if not rules:
            self.add_rule_row() # 如果没有规则，默认留一个空的
        else:
            for rule in rules:
                self.add_rule_row(rule.get("lp", ""), rule.get("rip", ""), rule.get("rp", ""))

    def browse_file(self):
        filepath = filedialog.askopenfilename(
            title="选择 gost.exe",
            filetypes=(("Executable files", "*.exe"), ("All files", "*.*"))
        )
        if filepath:
            self.cb_gost_path.set(filepath)

    def log(self, message):
        """线程安全的日志输出"""
        def append():
            self.txt_log.insert(tk.END, message + "\n")
            self.txt_log.see(tk.END)
        self.root.after(0, append)

    def toggle_connection(self):
        if self.process is None:
            self.start_gost()
        else:
            self.stop_gost()

    def start_gost(self):
        gost_path = self.cb_gost_path.get().strip()
        socks_ip = self.cb_socks_ip.get().strip()
        socks_port = self.cb_socks_port.get().strip()

        if not gost_path or not os.path.exists(gost_path):
            messagebox.showerror("错误", "Gost 路径不正确或文件不存在！")
            return
            
        if not socks_ip or not socks_port:
            messagebox.showerror("错误", "请填写 Socks5 IP 和端口！")
            return

        cmd = [gost_path]

        # 遍历添加所有 -L 规则
        valid_rules_count = 0
        for row in self.rule_rows:
            lp = row["lp"].get().strip()
            rip = row["rip"].get().strip()
            rp = row["rp"].get().strip()
            
            if lp and rip and rp:
                cmd.extend(["-L", f"tcp://127.0.0.1:{lp}/{rip}:{rp}"])
                valid_rules_count += 1

        if valid_rules_count == 0:
            messagebox.showwarning("警告", "请至少填写一组完整的端口转发规则！")
            return

        # 添加 -F 规则
        cmd.extend(["-F", f"socks5://{socks_ip}:{socks_port}"])

        # 保存当前状态以便下次直接使用
        self.save_config()

        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW

        self.log(f"[系统] 准备执行: {' '.join(cmd)}")

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=creationflags
            )

            self.btn_toggle.config(text="断  开")
            self.log("[系统] Gost 已启动。")

            threading.Thread(target=self.read_output, daemon=True).start()

        except Exception as e:
            self.log(f"[系统] 启动失败: {e}")
            self.process = None

    def stop_gost(self):
        if self.process:
            self.log("[系统] 正在停止 Gost...")
            self.process.terminate()
            self.process = None
            self.btn_toggle.config(text="连  接")
            self.log("[系统] Gost 已断开。")

    def read_output(self):
        try:
            for line in iter(self.process.stdout.readline, ''):
                if not line: break
                self.log(line.strip())
        except Exception:
            pass
        finally:
            if self.process:
                self.process = None
                self.root.after(0, lambda: self.btn_toggle.config(text="连  接"))
                self.log("[系统] 进程已结束。")

    def on_closing(self):
        self.save_config()
        if self.process:
            self.process.terminate()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = GostGUI(root)
    root.mainloop()