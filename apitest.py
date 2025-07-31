import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import requests
import json
import threading
import os
import hashlib
from datetime import datetime

class APITesterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🧪 API Tester (Postman Style) with Response Diff and Report")
        self.urls = []
        self.report_lines = []

        # UI setup
        tk.Label(root, text="API URL:").grid(row=0, column=0, sticky='w')
        self.url_entry = tk.Entry(root, width=80)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, columnspan=4)

        tk.Label(root, text="Method:").grid(row=1, column=0, sticky='w')
        self.method_var = tk.StringVar(root)
        self.method_var.set("GET")
        self.method_menu = tk.OptionMenu(root, self.method_var, "GET", "POST", "PUT", "DELETE")
        self.method_menu.grid(row=1, column=1, sticky='w')

        tk.Label(root, text="Headers (JSON):").grid(row=2, column=0, sticky='nw')
        self.headers_text = scrolledtext.ScrolledText(root, width=60, height=5)
        self.headers_text.grid(row=2, column=1, columnspan=4, padx=5, pady=5)

        tk.Label(root, text="Params (JSON):").grid(row=3, column=0, sticky='nw')
        self.params_text = scrolledtext.ScrolledText(root, width=60, height=3)
        self.params_text.grid(row=3, column=1, columnspan=4, padx=5, pady=5)

        tk.Label(root, text="Body (JSON or Text):").grid(row=4, column=0, sticky='nw')
        self.body_text = scrolledtext.ScrolledText(root, width=60, height=5)
        self.body_text.grid(row=4, column=1, columnspan=4, padx=5, pady=5)

        self.send_button = tk.Button(root, text="🚀 Send Request", command=self.send_request)
        self.send_button.grid(row=5, column=1, pady=5)

        self.load_file_button = tk.Button(root, text="📂 Load URLs (.txt)", command=self.load_urls_from_file)
        self.load_file_button.grid(row=5, column=2)

        self.batch_test_button = tk.Button(root, text="🧪 Test All URLs", command=self.batch_test)
        self.batch_test_button.grid(row=5, column=3)

        tk.Label(root, text="Response:").grid(row=6, column=0, sticky='nw')
        self.response_text = scrolledtext.ScrolledText(root, width=100, height=25)
        self.response_text.grid(row=6, column=1, columnspan=4, padx=5, pady=5)

        os.makedirs("responses", exist_ok=True)

    def parse_json_field(self, text_widget):
        text = text_widget.get("1.0", tk.END).strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except Exception as e:
            messagebox.showerror("Invalid JSON", f"Error parsing input:\n{e}")
            return None

    def send_request(self, url_override=None, log_batch=False):
        url = url_override or self.url_entry.get().strip()
        method = self.method_var.get()
        headers = self.parse_json_field(self.headers_text)
        params = self.parse_json_field(self.params_text)
        body = self.body_text.get("1.0", tk.END).strip()

        if headers is None or params is None:
            return

        try:
            json_body = json.loads(body) if body.startswith("{") else None
        except:
            json_body = None

        try:
            resp = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_body if json_body else None,
                data=body if not json_body else None
            )

            content = resp.text.strip()
            try:
                content_json = json.dumps(resp.json(), indent=4)
            except:
                content_json = content

            hashname = hashlib.md5(url.encode()).hexdigest()
            filename = os.path.join("responses", f"response_{hashname}.txt")

            previous_response = ""
            if os.path.exists(filename):
                with open(filename, "r", encoding="utf-8") as f:
                    previous_response = f.read()

            changed = previous_response.strip() != content.strip()
            status = "🔄 Changed" if changed else "🔁 Unchanged"

            # Save response to file
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)

            # Log to GUI
            result = (
                f"🌐 API Endpoint: {url}\n"
                f"🔧 Method: {method}\n"
                f"📥 Status: {resp.status_code}\n"
                f"🧾 Change: {status}\n\n"
                f"📤 Headers:\n{resp.headers}\n\n"
                f"📄 Body:\n{content_json}\n"
            )

            if not log_batch:
                self.response_text.delete("1.0", tk.END)
            self.response_text.insert(tk.END, result)
            self.response_text.insert(tk.END, "\n" + "-" * 80 + "\n")
            self.response_text.see(tk.END)

            # Save to report buffer if in batch
            if log_batch:
                short_response = content[:500].replace('\n', ' ').replace('\r', '')
                self.report_lines.append(
                    f"[{datetime.now().isoformat()}] {method} {url}\n"
                    f"Status: {resp.status_code} | Change: {status}\n"
                    f"Response (snippet): {short_response}\n"
                    f"{'-'*80}\n"
                )

        except Exception as e:
            err = f"\n❌ Error for {url}: {e}\n"
            self.response_text.insert(tk.END, err)
            self.report_lines.append(
                f"[{datetime.now().isoformat()}] {method} {url}\n"
                f"ERROR: {e}\n{'-'*80}\n"
            )

    def load_urls_from_file(self):
        file_path = filedialog.askopenfilename(title="Select .txt file with URLs", filetypes=[("Text Files", "*.txt")])
        if not file_path:
            return

        with open(file_path, "r") as f:
            self.urls = [line.strip() for line in f if line.strip()]

        messagebox.showinfo("Loaded", f"Loaded {len(self.urls)} URLs from file.")

    def batch_test(self):
        if not self.urls:
            messagebox.showerror("No URLs", "Load a .txt file with URLs first.")
            return

        self.report_lines.clear()
        threading.Thread(target=self._batch_test_thread, daemon=True).start()

    def _batch_test_thread(self):
        self.response_text.delete("1.0", tk.END)
        for idx, url in enumerate(self.urls, 1):
            self.response_text.insert(tk.END, f"\n🔍 Testing {idx}/{len(self.urls)}: {url}\n")
            self.send_request(url_override=url, log_batch=True)

        # Write to report file
        report_path = os.path.join("responses", "report.txt")
        with open(report_path, "w", encoding="utf-8") as report_file:
            report_file.writelines(self.report_lines)

        messagebox.showinfo("✅ Done", f"Batch test completed.\nReport saved to:\n{report_path}")


if __name__ == "__main__":
    root = tk.Tk()
    app = APITesterApp(root)
    root.mainloop()
