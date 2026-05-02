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
        self.root.title("Gost 代理控制台")
        self.root.geometry("600x550")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.process = None
        self.config = self.load_config()

        self.create_widgets()
        self.load_history_to_ui()

    def load_config(self):
        """加载历史配置文件"""
        default_config = {
            "gost_path": [],
            "local_port": ["33890"],
            "remote_ip": ["192.168.124.11"],
            "remote_port": ["3389"],
            "socks_ip": ["127.0.0.1"],
            "socks_port": ["7897"]
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved_config = json.load(f)
                    # 合并默认配置和历史配置
                    for k in default_config.keys():
                        if k in saved_config:
                            default_config[k] = saved_config[k]
            except Exception as e:
                print(f"读取配置文件失败: {e}")
        return default_config

    def save_config(self):
        """保存当前输入到历史配置文件，并去重"""
        current_values = {
            "gost_path": self.cb_gost_path.get(),
            "local_port": self.cb_local_port.get(),
            "remote_ip": self.cb_remote_ip.get(),
            "remote_port": self.cb_remote_port.get(),
            "socks_ip": self.cb_socks_ip.get(),
            "socks_port": self.cb_socks_port.get()
        }

        for key, val in current_values.items():
            if not val: continue
            # 将新值插入到列表最前面，并去除重复项
            if val in self.config[key]:
                self.config[key].remove(val)
            self.config[key].insert(0, val)
            # 限制历史记录最多保留 10 条
            self.config[key] = self.config[key][:10]

        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            self.log(f"[系统] 保存配置失败: {e}")

    def create_widgets(self):
        """绘制界面 UI"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ---- 参数设置区域 ----
        settings_frame = ttk.LabelFrame(main_frame, text="配置参数", padding="10")
        settings_frame.pack(fill=tk.X, pady=(0, 10))

        # 辅助函数：创建带 Label 的下拉框
        def create_input_row(parent, label_text, row, key):
            ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky=tk.W, pady=5)
            cb = ttk.Combobox(parent, width=30)
            cb.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
            return cb

        self.cb_gost_path = create_input_row(settings_frame, "Gost.exe 路径:", 0, "gost_path")
        btn_browse = ttk.Button(settings_frame, text="浏览...", command=self.browse_file)
        btn_browse.grid(row=0, column=2, padx=5, pady=5)

        self.cb_local_port = create_input_row(settings_frame, "本地端口:", 1, "local_port")
        self.cb_remote_ip = create_input_row(settings_frame, "远程 IP:", 2, "remote_ip")
        self.cb_remote_port = create_input_row(settings_frame, "远程端口:", 3, "remote_port")
        self.cb_socks_ip = create_input_row(settings_frame, "Socks5 代理 IP:", 4, "socks_ip")
        self.cb_socks_port = create_input_row(settings_frame, "Socks5 代理端口:", 5, "socks_port")

        settings_frame.columnconfigure(1, weight=1)

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

    def load_history_to_ui(self):
        """将加载的配置写入 UI 组件，并设置默认值为第一项"""
        def set_cb(cb, key):
            cb['values'] = self.config.get(key, [])
            if self.config.get(key):
                cb.set(self.config[key][0])

        set_cb(self.cb_gost_path, "gost_path")
        set_cb(self.cb_local_port, "local_port")
        set_cb(self.cb_remote_ip, "remote_ip")
        set_cb(self.cb_remote_port, "remote_port")
        set_cb(self.cb_socks_ip, "socks_ip")
        set_cb(self.cb_socks_port, "socks_port")

    def browse_file(self):
        filepath = filedialog.askopenfilename(
            title="选择 gost.exe",
            filetypes=(("Executable files", "*.exe"), ("All files", "*.*"))
        )
        if filepath:
            self.cb_gost_path.set(filepath)

    def log(self, message):
        """线程安全的日志输出函数"""
        def append():
            self.txt_log.insert(tk.END, message + "\n")
            self.txt_log.see(tk.END) # 自动滚动到底部
        self.root.after(0, append)

    def toggle_connection(self):
        if self.process is None:
            self.start_gost()
        else:
            self.stop_gost()

    def start_gost(self):
        gost_path = self.cb_gost_path.get().strip()
        local_port = self.cb_local_port.get().strip()
        remote_ip = self.cb_remote_ip.get().strip()
        remote_port = self.cb_remote_port.get().strip()
        socks_ip = self.cb_socks_ip.get().strip()
        socks_port = self.cb_socks_port.get().strip()

        if not all([gost_path, local_port, remote_ip, remote_port, socks_ip, socks_port]):
            messagebox.showwarning("参数不完整", "请填写所有必要的参数！")
            return
            
        if not os.path.exists(gost_path):
            messagebox.showerror("错误", f"找不到文件: {gost_path}")
            return

        # 保存配置历史
        self.save_config()
        self.load_history_to_ui() # 更新下拉框

        # 拼接命令：-L "tcp://127.0.0.1:33890/192.168.124.11:3389" -F "socks5://127.0.0.1:7897"
        cmd = [
            gost_path,
            "-L", f"tcp://127.0.0.1:{local_port}/{remote_ip}:{remote_port}",
            "-F", f"socks5://{socks_ip}:{socks_port}"
        ]

        # 隐藏 CMD 窗口的神奇参数 (仅限 Windows)
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW

        self.log(f"[系统] 准备执行: {' '.join(cmd)}")

        try:
            # 启动进程，捕获 stdout 和 stderr
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # 将错误输出合并到标准输出
                text=True,
                bufsize=1, # 行缓冲
                creationflags=creationflags
            )

            self.btn_toggle.config(text="断  开")
            self.log("[系统] Gost 已启动。")

            # 启动后台线程读取日志，避免卡死主界面
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
        """后台线程：持续读取 gost 的输出日志"""
        try:
            # 只要 process 存在且没结束就一直读
            for line in iter(self.process.stdout.readline, ''):
                if not line: break
                self.log(line.strip())
        except Exception as e:
            pass
        finally:
            # 如果进程自行退出（比如报错），重置按钮状态
            if self.process:
                self.process = None
                self.root.after(0, lambda: self.btn_toggle.config(text="连  接"))
                self.log("[系统] 进程已结束。")

    def on_closing(self):
        """窗口关闭时的清理工作"""
        self.save_config()
        if self.process:
            self.process.terminate()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = GostGUI(root)
    root.mainloop()