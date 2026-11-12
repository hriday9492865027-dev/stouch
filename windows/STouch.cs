using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Net.WebSockets;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace STouch
{
    static class Program
    {
        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new MainForm());
        }
    }

    public class MainForm : Form
    {
        private HttpListener _listener;
        private CancellationTokenSource _cts = new CancellationTokenSource();
        private Label _lblStatus;
        private Label _lblUrl;
        private Label _lblPin;
        private PictureBox _qrBox;
        private NotifyIcon _trayIcon;
        private string _localIp = "127.0.0.1";
        private int _port = 8000;
        private string _pin = "849201";
        private bool _connected = false;

        public MainForm()
        {
            InitializeComponent();
            _localIp = GetPrimaryLocalIP();
            _pin = new Random().Next(100000, 999999).ToString();

            _lblUrl.Text = $"http://{_localIp}:{_port}/";
            _lblPin.Text = $"PIN: {_pin}";

            LoadQrCode();
            StartServer();
        }

        private void InitializeComponent()
        {
            this.Text = "STouch - Wireless Touchpad Receiver";
            this.Size = new Size(420, 520);
            this.StartPosition = FormStartPosition.CenterScreen;
            this.FormBorderStyle = FormBorderStyle.FixedSingle;
            this.MaximizeBox = false;
            this.BackColor = Color.FromArgb(15, 23, 42); // Dark slate

            var lblTitle = new Label
            {
                Text = "DIGITAL TOUCHPAD",
                ForeColor = Color.FromArgb(56, 189, 248),
                Font = new Font("Segoe UI", 16, FontStyle.Bold),
                TextAlign = ContentAlignment.MiddleCenter,
                Dock = DockStyle.Top,
                Height = 45
            };
            this.Controls.Add(lblTitle);

            _lblStatus = new Label
            {
                Text = "● READY - WAITING FOR PHONE",
                ForeColor = Color.FromArgb(245, 158, 11),
                Font = new Font("Segoe UI", 10, FontStyle.Bold),
                TextAlign = ContentAlignment.MiddleCenter,
                Dock = DockStyle.Top,
                Height = 30
            };
            this.Controls.Add(_lblStatus);

            _qrBox = new PictureBox
            {
                Size = new Size(220, 220),
                Location = new Point(95, 85),
                SizeMode = PictureBoxSizeMode.CenterImage,
                BackColor = Color.White
            };
            this.Controls.Add(_qrBox);

            _lblPin = new Label
            {
                Text = "PIN: ...",
                ForeColor = Color.White,
                Font = new Font("Segoe UI", 14, FontStyle.Bold),
                TextAlign = ContentAlignment.MiddleCenter,
                Location = new Point(20, 315),
                Size = new Size(365, 30)
            };
            this.Controls.Add(_lblPin);

            _lblUrl = new Label
            {
                Text = "http://...",
                ForeColor = Color.FromArgb(148, 163, 184),
                Font = new Font("Segoe UI", 9, FontStyle.Regular),
                TextAlign = ContentAlignment.MiddleCenter,
                Location = new Point(20, 345),
                Size = new Size(365, 45)
            };
            this.Controls.Add(_lblUrl);

            var lblInstruction = new Label
            {
                Text = "Scan QR with your phone camera, or open the link above in your mobile browser.",
                ForeColor = Color.FromArgb(100, 116, 139),
                Font = new Font("Segoe UI", 8.5f, FontStyle.Regular),
                TextAlign = ContentAlignment.MiddleCenter,
                Location = new Point(20, 395),
                Size = new Size(365, 35)
            };
            this.Controls.Add(lblInstruction);

            var btnTray = new Button
            {
                Text = "Minimize to System Tray",
                ForeColor = Color.White,
                BackColor = Color.FromArgb(30, 41, 59),
                FlatStyle = FlatStyle.Flat,
                Font = new Font("Segoe UI", 9, FontStyle.Bold),
                Location = new Point(110, 435),
                Size = new Size(190, 32)
            };
            btnTray.FlatAppearance.BorderColor = Color.FromArgb(56, 189, 248);
            btnTray.Click += (s, e) => { this.Hide(); };
            this.Controls.Add(btnTray);

            // Tray Icon
            _trayIcon = new NotifyIcon
            {
                Icon = SystemIcons.Application,
                Text = "STouch Touchpad Receiver",
                Visible = true
            };
            _trayIcon.DoubleClick += (s, e) => { this.Show(); this.WindowState = FormWindowState.Normal; };

            var menu = new ContextMenuStrip();
            menu.Items.Add("Open STouch", null, (s, e) => { this.Show(); this.WindowState = FormWindowState.Normal; });
            menu.Items.Add("Exit", null, (s, e) => { Application.Exit(); });
            _trayIcon.ContextMenuStrip = menu;
        }

        private void LoadQrCode()
        {
            Task.Run(() =>
            {
                try
                {
                    string targetUrl = $"https://stouch-client.vercel.app/?pc={_localIp}:{_port}";
                    string qrApi = $"https://api.qrserver.com/v1/create-qr-code/?size=200x200&margin=2&data={Uri.EscapeDataString(targetUrl)}";
                    using (var wc = new WebClient())
                    {
                        byte[] bytes = wc.DownloadData(qrApi);
                        using (var ms = new MemoryStream(bytes))
                        {
                            var bmp = new Bitmap(ms);
                            this.Invoke(new Action(() => _qrBox.Image = bmp));
                        }
                    }
                }
                catch
                {
                    // Fallback visual block if offline
                    var fallback = new Bitmap(200, 200);
                    using (var g = Graphics.FromImage(fallback))
                    {
                        g.Clear(Color.White);
                        g.DrawString("SCAN OR OPEN\n" + _localIp + ":" + _port,
                            new Font("Segoe UI", 10, FontStyle.Bold), Brushes.Black, 20, 80);
                    }
                    this.Invoke(new Action(() => _qrBox.Image = fallback));
                }
            });
        }

        private string GetPrimaryLocalIP()
        {
            try
            {
                using (var socket = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, 0))
                {
                    socket.Connect("8.8.8.8", 65530);
                    var endPoint = socket.LocalEndPoint as IPEndPoint;
                    return endPoint.Address.ToString();
                }
            }
            catch
            {
                return "127.0.0.1";
            }
        }

        private async void StartServer()
        {
            try
            {
                _listener = new HttpListener();
                _listener.Prefixes.Add($"http://*:{_port}/");
                _listener.Start();

                while (!_cts.IsCancellationRequested)
                {
                    var ctx = await _listener.GetContextAsync();
                    if (ctx.Request.IsWebSocketRequest)
                    {
                        ProcessWebSocketRequest(ctx);
                    }
                    else
                    {
                        ServeHttp(ctx);
                    }
                }
            }
            catch (Exception ex)
            {
                Debug.WriteLine("Server error: " + ex.Message);
            }
        }

        private async void ProcessWebSocketRequest(HttpListenerContext ctx)
        {
            WebSocketContext wsCtx = null;
            try
            {
                wsCtx = await ctx.AcceptWebSocketAsync(null);
                UpdateConnectionState(true);

                var ws = wsCtx.WebSocket;
                byte[] buffer = new byte[4096];

                while (ws.State == WebSocketState.Open && !_cts.IsCancellationRequested)
                {
                    var result = await ws.ReceiveAsync(new ArraySegment<byte>(buffer), CancellationToken.None);
                    if (result.MessageType == WebSocketMessageType.Close)
                    {
                        await ws.CloseAsync(WebSocketCloseStatus.NormalClosure, "Closing", CancellationToken.None);
                        break;
                    }
                    else if (result.MessageType == WebSocketMessageType.Text)
                    {
                        string msg = Encoding.UTF8.GetString(buffer, 0, result.Count);
                        HandleIncomingMessage(ws, msg);
                    }
                }
            }
            catch (Exception ex)
            {
                Debug.WriteLine("WS error: " + ex.Message);
            }
            finally
            {
                // Safety Watchdog: Release all held inputs immediately on disconnect
                InputManager.ReleaseAll();
                UpdateConnectionState(false);
            }
        }

        private void HandleIncomingMessage(WebSocket ws, string json)
        {
            try
            {
                if (json.Contains("\"SESSION_HELLO\""))
                {
                    string reply = "{\"version\":\"2.0\",\"type\":\"SESSION_READY\",\"payload\":{\"host_name\":\"" +
                        Environment.MachineName + "\",\"status\":\"ok\"}}";
                    byte[] b = Encoding.UTF8.GetBytes(reply);
                    ws.SendAsync(new ArraySegment<byte>(b), WebSocketMessageType.Text, true, CancellationToken.None);
                }
                else if (json.Contains("\"POINTER_MOVE\""))
                {
                    int dx = ParseInt(json, "\"dx\":", 0);
                    int dy = ParseInt(json, "\"dy\":", 0);
                    InputManager.MouseMove(dx, dy);
                }
                else if (json.Contains("\"BUTTON_STATE\""))
                {
                    string button = ParseString(json, "\"button\":\"", "left");
                    string state = ParseString(json, "\"state\":\"", "click");
                    InputManager.MouseButton(button, state);
                }
                else if (json.Contains("\"SCROLL\""))
                {
                    int dx = ParseInt(json, "\"dx\":", 0);
                    int dy = ParseInt(json, "\"dy\":", 0);
                    InputManager.MouseScroll(dx, dy);
                }
                else if (json.Contains("\"ACTION_REQUEST\""))
                {
                    string action = ParseString(json, "\"action\":\"", "");
                    InputManager.ExecuteAction(action);
                }
                else if (json.Contains("\"HEARTBEAT\""))
                {
                    string reply = "{\"version\":\"2.0\",\"type\":\"HEARTBEAT\",\"payload\":{\"echo\":1}}";
                    byte[] b = Encoding.UTF8.GetBytes(reply);
                    ws.SendAsync(new ArraySegment<byte>(b), WebSocketMessageType.Text, true, CancellationToken.None);
                }
                else if (json.Contains("\"RELEASE_ALL\""))
                {
                    InputManager.ReleaseAll();
                }
            }
            catch { }
        }

        private int ParseInt(string json, string key, int def)
        {
            int idx = json.IndexOf(key);
            if (idx == -1) return def;
            idx += key.Length;
            int end = json.IndexOfAny(new[] { ',', '}', ' ' }, idx);
            if (end == -1) end = json.Length;
            string s = json.Substring(idx, end - idx).Trim();
            int v;
            return int.TryParse(s, out v) ? v : def;
        }

        private string ParseString(string json, string key, string def)
        {
            int idx = json.IndexOf(key);
            if (idx == -1) return def;
            idx += key.Length;
            int end = json.IndexOf('"', idx);
            if (end == -1) return def;
            return json.Substring(idx, end - idx);
        }

        private void ServeHttp(HttpListenerContext ctx)
        {
            // Simple response for direct browser check
            string html = "<html><body style='font-family:sans-serif;background:#0f172a;color:#fff;text-align:center;padding:50px;'>" +
                "<h1>STouch Windows Receiver Running!</h1>" +
                "<p>Connect with your phone at <a style='color:#38bdf8' href='https://stouch-client.vercel.app/?pc=" + _localIp + ":" + _port + "'>" +
                "https://stouch-client.vercel.app</a></p></body></html>";
            byte[] buf = Encoding.UTF8.GetBytes(html);
            ctx.Response.ContentType = "text/html";
            ctx.Response.ContentLength64 = buf.Length;
            ctx.Response.OutputStream.Write(buf, 0, buf.Length);
            ctx.Response.Close();
        }

        private void UpdateConnectionState(bool connected)
        {
            _connected = connected;
            if (this.IsHandleCreated)
            {
                this.Invoke(new Action(() =>
                {
                    if (connected)
                    {
                        _lblStatus.Text = "● PHONE CONNECTED";
                        _lblStatus.ForeColor = Color.FromArgb(16, 185, 129); // Green
                    }
                    else
                    {
                        _lblStatus.Text = "● READY - WAITING FOR PHONE";
                        _lblStatus.ForeColor = Color.FromArgb(245, 158, 11); // Amber
                    }
                }));
            }
        }

        protected override void OnFormClosing(FormClosingEventArgs e)
        {
            if (e.CloseReason == CloseReason.UserClosing)
            {
                e.Cancel = true;
                this.Hide();
                _trayIcon.ShowBalloonTip(2000, "STouch", "Running in background in the system tray.", ToolTipIcon.Info);
            }
            else
            {
                _cts.Cancel();
                _listener?.Stop();
                _trayIcon.Visible = false;
                InputManager.ReleaseAll();
                base.OnFormClosing(e);
            }
        }
    }

    public static class InputManager
    {
        [DllImport("user32.dll", SetLastError = true)]
        private static extern uint SendInput(uint nInputs, INPUT[] pInputs, int cbSize);

        [DllImport("user32.dll")]
        private static extern bool LockWorkStation();

        private const int INPUT_MOUSE = 0;
        private const int INPUT_KEYBOARD = 1;

        private const uint MOUSEEVENTF_MOVE = 0x0001;
        private const uint MOUSEEVENTF_LEFTDOWN = 0x0002;
        private const uint MOUSEEVENTF_LEFTUP = 0x0004;
        private const uint MOUSEEVENTF_RIGHTDOWN = 0x0008;
        private const uint MOUSEEVENTF_RIGHTUP = 0x0010;
        private const uint MOUSEEVENTF_MIDDLEDOWN = 0x0020;
        private const uint MOUSEEVENTF_MIDDLEUP = 0x0040;
        private const uint MOUSEEVENTF_WHEEL = 0x0800;
        private const uint MOUSEEVENTF_HWHEEL = 0x1000;

        private const uint KEYEVENTF_KEYUP = 0x0002;
        private const uint KEYEVENTF_EXTENDEDKEY = 0x0001;

        public static readonly HashSet<string> HeldButtons = new HashSet<string>();
        public static readonly HashSet<ushort> HeldKeys = new HashSet<ushort>();

        public static void MouseMove(int dx, int dy)
        {
            dx = Math.Max(-500, Math.Min(500, dx));
            dy = Math.Max(-500, Math.Min(500, dy));
            var inputs = new INPUT[1];
            inputs[0].type = INPUT_MOUSE;
            inputs[0].u.mi.dx = dx;
            inputs[0].u.mi.dy = dy;
            inputs[0].u.mi.dwFlags = MOUSEEVENTF_MOVE;
            SendInput(1, inputs, Marshal.SizeOf(typeof(INPUT)));
        }

        public static void MouseButton(string button, string state)
        {
            button = button.ToLower();
            uint down = (button == "right") ? MOUSEEVENTF_RIGHTDOWN : ((button == "middle") ? MOUSEEVENTF_MIDDLEDOWN : MOUSEEVENTF_LEFTDOWN);
            uint up = (button == "right") ? MOUSEEVENTF_RIGHTUP : ((button == "middle") ? MOUSEEVENTF_MIDDLEUP : MOUSEEVENTF_LEFTUP);

            if (state == "click")
            {
                var inputs = new INPUT[2];
                inputs[0].type = INPUT_MOUSE; inputs[0].u.mi.dwFlags = down;
                inputs[1].type = INPUT_MOUSE; inputs[1].u.mi.dwFlags = up;
                SendInput(2, inputs, Marshal.SizeOf(typeof(INPUT)));
                HeldButtons.Remove(button);
            }
            else if (state == "double_click")
            {
                var inputs = new INPUT[4];
                inputs[0].type = INPUT_MOUSE; inputs[0].u.mi.dwFlags = down;
                inputs[1].type = INPUT_MOUSE; inputs[1].u.mi.dwFlags = up;
                inputs[2].type = INPUT_MOUSE; inputs[2].u.mi.dwFlags = down;
                inputs[3].type = INPUT_MOUSE; inputs[3].u.mi.dwFlags = up;
                SendInput(4, inputs, Marshal.SizeOf(typeof(INPUT)));
                HeldButtons.Remove(button);
            }
            else if (state == "down")
            {
                var inputs = new INPUT[1];
                inputs[0].type = INPUT_MOUSE; inputs[0].u.mi.dwFlags = down;
                SendInput(1, inputs, Marshal.SizeOf(typeof(INPUT)));
                HeldButtons.Add(button);
            }
            else if (state == "up")
            {
                var inputs = new INPUT[1];
                inputs[0].type = INPUT_MOUSE; inputs[0].u.mi.dwFlags = up;
                SendInput(1, inputs, Marshal.SizeOf(typeof(INPUT)));
                HeldButtons.Remove(button);
            }
        }

        public static void MouseScroll(int dx, int dy)
        {
            var list = new List<INPUT>();
            if (dy != 0)
            {
                var inv = new INPUT { type = INPUT_MOUSE };
                inv.u.mi.dwFlags = MOUSEEVENTF_WHEEL;
                inv.u.mi.mouseData = (uint)(dy * 20);
                list.Add(inv);
            }
            if (dx != 0)
            {
                var inh = new INPUT { type = INPUT_MOUSE };
                inh.u.mi.dwFlags = MOUSEEVENTF_HWHEEL;
                inh.u.mi.mouseData = (uint)(dx * 20);
                list.Add(inh);
            }
            if (list.Count > 0)
            {
                SendInput((uint)list.Count, list.ToArray(), Marshal.SizeOf(typeof(INPUT)));
            }
        }

        public static void SendKeyChord(params ushort[] vkCodes)
        {
            var list = new List<INPUT>();
            foreach (var vk in vkCodes)
            {
                var inp = new INPUT { type = INPUT_KEYBOARD };
                inp.u.ki.wVk = vk;
                inp.u.ki.dwFlags = (vk == 0x5B || vk == 0x5C) ? KEYEVENTF_EXTENDEDKEY : 0;
                list.Add(inp);
            }
            for (int i = vkCodes.Length - 1; i >= 0; i--)
            {
                var vk = vkCodes[i];
                var inp = new INPUT { type = INPUT_KEYBOARD };
                inp.u.ki.wVk = vk;
                inp.u.ki.dwFlags = KEYEVENTF_KEYUP | ((vk == 0x5B || vk == 0x5C) ? KEYEVENTF_EXTENDEDKEY : 0);
                list.Add(inp);
            }
            SendInput((uint)list.Count, list.ToArray(), Marshal.SizeOf(typeof(INPUT)));
        }

        public static void ExecuteAction(string action)
        {
            switch (action.ToLower())
            {
                case "show_desktop": SendKeyChord(0x5B, 0x44); break; // Win + D
                case "task_view": SendKeyChord(0x5B, 0x09); break; // Win + Tab
                case "app_switch": SendKeyChord(0x12, 0x09); break; // Alt + Tab
                case "windows_search": SendKeyChord(0x5B, 0x53); break; // Win + S
                case "task_manager": SendKeyChord(0x11, 0x10, 0x1B); break; // Ctrl + Shift + Esc
                case "file_explorer": SendKeyChord(0x5B, 0x45); break; // Win + E
                case "screenshot": SendKeyChord(0x5B, 0x10, 0x53); break; // Win + Shift + S
                case "lock_workstation": LockWorkStation(); break;
                case "vol_up": SendKeyChord(0xAF); break;
                case "vol_down": SendKeyChord(0xAE); break;
                case "vol_mute": SendKeyChord(0xAD); break;
                case "media_playpause": SendKeyChord(0xB3); break;
                case "media_next": SendKeyChord(0xB0); break;
                case "media_prev": SendKeyChord(0xB1); break;
                case "media_fullscreen": SendKeyChord(0x46); break; // F
                case "presenter_next": SendKeyChord(0x22); break; // Page Down
                case "presenter_prev": SendKeyChord(0x21); break; // Page Up
                case "presenter_start": SendKeyChord(0x74); break; // F5
                case "presenter_black": SendKeyChord(0x42); break; // B
                case "presenter_end": SendKeyChord(0x1B); break; // Esc
            }
        }

        public static void ReleaseAll()
        {
            var list = new List<INPUT>();
            foreach (var b in HeldButtons)
            {
                uint up = (b == "right") ? MOUSEEVENTF_RIGHTUP : ((b == "middle") ? MOUSEEVENTF_MIDDLEUP : MOUSEEVENTF_LEFTUP);
                var inp = new INPUT { type = INPUT_MOUSE };
                inp.u.mi.dwFlags = up;
                list.Add(inp);
            }
            HeldButtons.Clear();

            foreach (var k in HeldKeys)
            {
                var inp = new INPUT { type = INPUT_KEYBOARD };
                inp.u.ki.wVk = k;
                inp.u.ki.dwFlags = KEYEVENTF_KEYUP;
                list.Add(inp);
            }
            HeldKeys.Clear();

            if (list.Count > 0)
            {
                SendInput((uint)list.Count, list.ToArray(), Marshal.SizeOf(typeof(INPUT)));
            }
        }

        [StructLayout(LayoutKind.Sequential)]
        struct MOUSEINPUT
        {
            public int dx;
            public int dy;
            public uint mouseData;
            public uint dwFlags;
            public uint time;
            public IntPtr dwExtraInfo;
        }

        [StructLayout(LayoutKind.Sequential)]
        struct KEYBDINPUT
        {
            public ushort wVk;
            public ushort wScan;
            public uint dwFlags;
            public uint time;
            public IntPtr dwExtraInfo;
        }

        [StructLayout(LayoutKind.Explicit)]
        struct INPUTUNION
        {
            [FieldOffset(0)] public MOUSEINPUT mi;
            [FieldOffset(0)] public KEYBDINPUT ki;
        }

        [StructLayout(LayoutKind.Sequential)]
        struct INPUT
        {
            public int type;
            public INPUTUNION u;
        }
    }
}
