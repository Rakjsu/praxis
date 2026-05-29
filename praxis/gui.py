"""Interface gráfica (Tkinter) do Praxis."""

from __future__ import annotations

import threading
import time
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

from . import __app_name__, __version__, config, screen, updater
from .engine import MacroEngine
from .hotkeys import HotkeyManager
from .models import PotionRule, Profile, Settings, Skill
from .overlay import StatusOverlay
from .sender import available_keys

KEY_VALUES = available_keys()


def _virtual_desktop() -> tuple[int, int, int, int]:
    """Retorna (x, y, largura, altura) do desktop virtual (todos os monitores)."""
    try:
        import ctypes

        g = ctypes.windll.user32.GetSystemMetrics
        return g(76), g(77), g(78), g(79)  # X/Y/CX/CY VIRTUALSCREEN
    except Exception:
        return 0, 0, 0, 0


class RegionSelector(tk.Toplevel):
    """Overlay que cobre todos os monitores para selecionar uma região.

    O retângulo é desenhado em coordenadas do canvas (relativas ao canto do
    desktop virtual), mas o resultado é salvo em coordenadas absolutas de tela.
    """

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.result: list[int] | None = None

        vx, vy, vw, vh = _virtual_desktop()
        self._offset = (vx, vy)
        if vw > 0 and vh > 0:
            self.overrideredirect(True)
            self.geometry(f"{vw}x{vh}+{vx}+{vy}")
        else:
            self.attributes("-fullscreen", True)

        self.attributes("-alpha", 0.3)
        self.attributes("-topmost", True)
        self.configure(bg="black", cursor="cross")
        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self._start: tuple[int, int] | None = None
        self._rect = None
        self.canvas.bind("<ButtonPress-1>", self._down)
        self.canvas.bind("<B1-Motion>", self._move)
        self.canvas.bind("<ButtonRelease-1>", self._up)
        self.bind("<Escape>", lambda _e: self._cancel())
        self.canvas.create_text(
            max(1, vw) // 2, 30,
            text="Arraste sobre a barra de vida — ESC para cancelar",
            fill="white", font=("Segoe UI", 14),
        )

    def _to_canvas(self, x_root: int, y_root: int) -> tuple[int, int]:
        return x_root - self._offset[0], y_root - self._offset[1]

    def _down(self, e: tk.Event) -> None:
        self._start = (e.x_root, e.y_root)
        if self._rect:
            self.canvas.delete(self._rect)
        cx, cy = self._to_canvas(e.x_root, e.y_root)
        self._rect = self.canvas.create_rectangle(cx, cy, cx, cy, outline="red", width=2)

    def _move(self, e: tk.Event) -> None:
        if self._start and self._rect:
            cx0, cy0 = self._to_canvas(*self._start)
            cx1, cy1 = self._to_canvas(e.x_root, e.y_root)
            self.canvas.coords(self._rect, cx0, cy0, cx1, cy1)

    def _up(self, e: tk.Event) -> None:
        if not self._start:
            return
        x1, y1 = self._start
        x2, y2 = e.x_root, e.y_root
        self.result = [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


class SkillRow:
    """Uma linha editável de skill dentro da tabela."""

    def __init__(self, parent: tk.Misc, skill: Skill, on_remove) -> None:
        self.enabled = tk.BooleanVar(value=skill.enabled)
        self.name = tk.StringVar(value=skill.name)
        self.key = tk.StringVar(value=skill.key)
        self.interval = tk.IntVar(value=skill.interval_ms)

        self.frame = ttk.Frame(parent)
        ttk.Checkbutton(self.frame, variable=self.enabled).grid(row=0, column=0, padx=2)
        ttk.Entry(self.frame, textvariable=self.name, width=16).grid(row=0, column=1, padx=2)
        ttk.Combobox(
            self.frame, textvariable=self.key, values=KEY_VALUES, width=10
        ).grid(row=0, column=2, padx=2)
        ttk.Spinbox(
            self.frame, from_=50, to=600000, increment=50,
            textvariable=self.interval, width=8,
        ).grid(row=0, column=3, padx=2)
        ttk.Button(self.frame, text="X", width=3,
                   command=lambda: on_remove(self)).grid(row=0, column=4, padx=2)
        self.frame.pack(fill="x", pady=1)

    def to_skill(self) -> Skill:
        return Skill(
            name=self.name.get().strip() or "Skill",
            key=self.key.get().strip().lower() or "1",
            interval_ms=max(50, int(self.interval.get() or 50)),
            enabled=self.enabled.get(),
        )

    def destroy(self) -> None:
        self.frame.destroy()


class OptionsDialog(tk.Toplevel):
    """Janela de opções globais (Settings)."""

    def __init__(self, app: "MacroApp") -> None:
        super().__init__(app)
        self.app = app
        self.title("Opções")
        self.resizable(False, False)
        self.transient(app)
        self.grab_set()

        s = app.settings
        self.start_minimized = tk.BooleanVar(value=s.start_minimized)
        self.overlay_enabled = tk.BooleanVar(value=s.overlay_enabled)
        self.log_to_file = tk.BooleanVar(value=s.log_to_file)
        self.panic_key = tk.StringVar(value=s.panic_key)

        pad = {"padx": 10, "pady": 4}
        ttk.Checkbutton(self, text="Iniciar minimizado",
                        variable=self.start_minimized).grid(row=0, column=0, columnspan=2, sticky="w", **pad)
        ttk.Checkbutton(self, text="Mostrar overlay de status",
                        variable=self.overlay_enabled).grid(row=1, column=0, columnspan=2, sticky="w", **pad)
        ttk.Checkbutton(self, text="Salvar log em arquivo (praxis.log)",
                        variable=self.log_to_file).grid(row=2, column=0, columnspan=2, sticky="w", **pad)
        ttk.Label(self, text="Tecla de pânico (para tudo):").grid(row=3, column=0, sticky="w", **pad)
        ttk.Combobox(self, textvariable=self.panic_key, values=KEY_VALUES,
                     width=10).grid(row=3, column=1, sticky="w", **pad)

        btns = ttk.Frame(self)
        btns.grid(row=4, column=0, columnspan=2, pady=8)
        ttk.Button(btns, text="Salvar", command=self._save).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side="left", padx=4)

    def _save(self) -> None:
        self.app.settings = Settings(
            start_minimized=self.start_minimized.get(),
            overlay_enabled=self.overlay_enabled.get(),
            panic_key=self.panic_key.get().strip().lower() or "f9",
            log_to_file=self.log_to_file.get(),
        )
        config.save_settings(self.app.settings)
        self.app._apply_settings()
        self.app.log("Opções salvas.")
        self.destroy()


class MacroApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{__app_name__} v{__version__}")
        self.geometry("620x760")
        self.minsize(560, 660)

        self.engine = MacroEngine(log=self.log)
        self.hotkeys = HotkeyManager()
        self.panic_hotkeys = HotkeyManager()
        self.skill_rows: list[SkillRow] = []
        self._pending_update: updater.UpdateInfo | None = None
        self.settings = config.load_settings()
        self.overlay: StatusOverlay | None = None

        self._build()
        self._load_initial_profile()
        self._apply_settings()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(400, self._refresh_status)
        self.after(1500, self._check_update_async)
        if self.settings.start_minimized:
            self.iconify()

    # --- construção da UI --------------------------------------------------

    def _build(self) -> None:
        pad = {"padx": 8, "pady": 4}

        # Barra de perfis
        top = ttk.LabelFrame(self, text="Perfil")
        top.pack(fill="x", **pad)
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(
            top, textvariable=self.profile_var, state="readonly", width=24
        )
        self.profile_combo.grid(row=0, column=0, padx=4, pady=6)
        self.profile_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_pick_profile())
        ttk.Button(top, text="Novo", command=self._new_profile).grid(row=0, column=1, padx=2)
        ttk.Button(top, text="Salvar", command=self._save_profile).grid(row=0, column=2, padx=2)
        ttk.Button(top, text="Excluir", command=self._delete_profile).grid(row=0, column=3, padx=2)
        ttk.Button(top, text="Opções", command=self._open_options).grid(row=0, column=4, padx=2)

        # Nome + hotkey
        meta = ttk.Frame(self)
        meta.pack(fill="x", **pad)
        ttk.Label(meta, text="Nome:").grid(row=0, column=0, sticky="w")
        self.name_var = tk.StringVar()
        ttk.Entry(meta, textvariable=self.name_var, width=24).grid(row=0, column=1, padx=4)
        ttk.Label(meta, text="Hotkey liga/desliga:").grid(row=0, column=2, sticky="w", padx=(12, 0))
        self.hotkey_var = tk.StringVar()
        ttk.Entry(meta, textvariable=self.hotkey_var, width=8).grid(row=0, column=3, padx=4)
        ttk.Button(meta, text="Aplicar hotkey", command=self._apply_hotkey).grid(row=0, column=4)

        # Skills
        sk = ttk.LabelFrame(self, text="Rotação de Skills")
        sk.pack(fill="both", **pad)
        header = ttk.Frame(sk)
        header.pack(fill="x")
        for i, txt in enumerate(["On", "Nome", "Tecla", "ms"]):
            ttk.Label(header, text=txt, width=[4, 16, 11, 9][i],
                      anchor="w").grid(row=0, column=i, padx=2)
        self.skills_container = ttk.Frame(sk)
        self.skills_container.pack(fill="both", expand=True)
        ttk.Button(sk, text="+ Adicionar skill",
                   command=lambda: self._add_skill_row(Skill())).pack(anchor="w", pady=4)

        # Poção
        pt = ttk.LabelFrame(self, text="Auto-Poção (vida)")
        pt.pack(fill="x", **pad)
        self.pot_enabled = tk.BooleanVar()
        ttk.Checkbutton(pt, text="Ativar", variable=self.pot_enabled).grid(
            row=0, column=0, sticky="w", padx=4, pady=2)
        ttk.Label(pt, text="Tecla:").grid(row=0, column=1, sticky="e")
        self.pot_key = tk.StringVar()
        ttk.Combobox(pt, textvariable=self.pot_key, values=KEY_VALUES, width=10).grid(
            row=0, column=2, padx=4)

        ttk.Label(pt, text="Região:").grid(row=1, column=0, sticky="e", padx=4)
        self.region_var = tk.StringVar(value="(não definida)")
        ttk.Label(pt, textvariable=self.region_var).grid(row=1, column=1, columnspan=2, sticky="w")
        ttk.Button(pt, text="Selecionar região", command=self._select_region).grid(
            row=1, column=3, padx=4)
        ttk.Button(pt, text="Detectar cor", command=self._detect_color).grid(
            row=1, column=4, padx=4)

        ttk.Label(pt, text="Disparar abaixo de (%):").grid(row=2, column=0, columnspan=2, sticky="e")
        self.pot_threshold = tk.IntVar(value=45)
        ttk.Spinbox(pt, from_=1, to=99, textvariable=self.pot_threshold, width=6).grid(
            row=2, column=2, padx=4, sticky="w")
        ttk.Label(pt, text="Cooldown (ms):").grid(row=2, column=3, sticky="e")
        self.pot_cooldown = tk.IntVar(value=2000)
        ttk.Spinbox(pt, from_=100, to=60000, increment=100,
                    textvariable=self.pot_cooldown, width=8).grid(row=2, column=4, padx=4)

        ttk.Label(pt, text="Cor da vida (R,G,B):").grid(row=3, column=0, columnspan=2, sticky="e")
        self.pot_color = tk.StringVar(value="190,30,30")
        ttk.Entry(pt, textvariable=self.pot_color, width=12).grid(row=3, column=2, sticky="w", padx=4)
        ttk.Label(pt, text="Tolerância:").grid(row=3, column=3, sticky="e")
        self.pot_tol = tk.IntVar(value=70)
        ttk.Spinbox(pt, from_=5, to=200, textvariable=self.pot_tol, width=6).grid(
            row=3, column=4, padx=4, sticky="w")
        ttk.Button(pt, text="Testar leitura", command=self._test_read).grid(
            row=4, column=0, columnspan=2, sticky="w", padx=4, pady=4)

        # Controle + status
        ctrl = ttk.Frame(self)
        ctrl.pack(fill="x", **pad)
        self.toggle_btn = ttk.Button(ctrl, text="▶ Iniciar (OFF)", command=self._toggle)
        self.toggle_btn.pack(side="left")
        self.status_lbl = ttk.Label(ctrl, text="parado", foreground="gray")
        self.status_lbl.pack(side="left", padx=10)
        ttk.Button(ctrl, text="Verificar atualizações",
                   command=self._check_update_async).pack(side="right")

        # Faixa de atualização (oculta até haver versão nova)
        self.update_bar = ttk.Frame(self)
        self.update_lbl = ttk.Label(self.update_bar, foreground="#7a3cff")
        self.update_lbl.pack(side="left", padx=4)
        self.update_btn = ttk.Button(self.update_bar, text="Atualizar agora",
                                     command=self._apply_update)
        self.update_btn.pack(side="left", padx=4)

        # Log
        logf = ttk.LabelFrame(self, text="Log")
        logf.pack(fill="both", expand=True, **pad)
        self.log_text = tk.Text(logf, height=8, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True)

    # --- skills ------------------------------------------------------------

    def _add_skill_row(self, skill: Skill) -> None:
        row = SkillRow(self.skills_container, skill, self._remove_skill_row)
        self.skill_rows.append(row)

    def _remove_skill_row(self, row: SkillRow) -> None:
        row.destroy()
        self.skill_rows.remove(row)

    def _clear_skills(self) -> None:
        for row in list(self.skill_rows):
            row.destroy()
        self.skill_rows.clear()

    # --- perfis ------------------------------------------------------------

    def _refresh_profile_list(self, select: str | None = None) -> None:
        names = config.list_profiles()
        self.profile_combo["values"] = names
        if select and select in names:
            self.profile_var.set(select)
        elif names and not self.profile_var.get():
            self.profile_var.set(names[0])

    def _load_initial_profile(self) -> None:
        self._refresh_profile_list()
        names = config.list_profiles()
        if names:
            self.profile_var.set(names[0])
            self._on_pick_profile()
        else:
            self._apply_profile_to_form(Profile(name="Diablo", toggle_hotkey="f8"))

    def _on_pick_profile(self) -> None:
        stem = self.profile_var.get()
        if not stem:
            return
        try:
            profile = config.load_profile(stem)
        except Exception as exc:
            messagebox.showerror("Erro", f"Falha ao carregar perfil: {exc}")
            return
        self._apply_profile_to_form(profile)
        self._apply_hotkey()

    def _apply_profile_to_form(self, profile: Profile) -> None:
        self.name_var.set(profile.name)
        self.hotkey_var.set(profile.toggle_hotkey)
        self._clear_skills()
        for skill in profile.skills:
            self._add_skill_row(skill)
        if not profile.skills:
            self._add_skill_row(Skill())
        p = profile.potion
        self.pot_enabled.set(p.enabled)
        self.pot_key.set(p.key)
        self.region_var.set(str(p.region) if any(p.region) else "(não definida)")
        self.pot_threshold.set(int(p.threshold_pct * 100))
        self.pot_cooldown.set(p.cooldown_ms)
        self.pot_color.set(",".join(str(c) for c in p.color))
        self.pot_tol.set(p.tolerance)

    def _form_to_profile(self) -> Profile:
        return Profile(
            name=self.name_var.get().strip() or "Perfil",
            toggle_hotkey=self.hotkey_var.get().strip().lower() or "f8",
            skills=[r.to_skill() for r in self.skill_rows],
            potion=self._form_to_potion(),
        )

    def _form_to_potion(self) -> PotionRule:
        try:
            color = [int(c) for c in self.pot_color.get().split(",")][:3]
            if len(color) != 3:
                raise ValueError
        except Exception:
            color = [190, 30, 30]
        region = self._parse_region()
        return PotionRule(
            enabled=self.pot_enabled.get(),
            key=self.pot_key.get().strip().lower() or "q",
            region=region,
            color=color,
            tolerance=int(self.pot_tol.get() or 70),
            threshold_pct=int(self.pot_threshold.get() or 45) / 100,
            cooldown_ms=int(self.pot_cooldown.get() or 2000),
        )

    def _parse_region(self) -> list[int]:
        raw = self.region_var.get().strip("()[] ")
        try:
            parts = [int(x.strip()) for x in raw.split(",")]
            if len(parts) == 4:
                return parts
        except Exception:
            pass
        return [0, 0, 0, 0]

    def _new_profile(self) -> None:
        self.profile_var.set("")
        self._apply_profile_to_form(Profile(name="Novo Perfil", toggle_hotkey="f8"))

    def _save_profile(self) -> None:
        profile = self._form_to_profile()
        path = config.save_profile(profile)
        self._refresh_profile_list(select=path.stem)
        self.engine.set_profile(profile)
        self.log(f"Perfil salvo: {path.name}")

    def _delete_profile(self) -> None:
        stem = self.profile_var.get()
        if not stem:
            return
        if messagebox.askyesno("Excluir", f"Excluir o perfil '{stem}'?"):
            config.delete_profile(stem)
            self.profile_var.set("")
            self._refresh_profile_list()
            self.log(f"Perfil excluído: {stem}")

    # --- poção: helpers ----------------------------------------------------

    def _select_region(self) -> None:
        self.withdraw()
        self.update()
        time.sleep(0.2)
        sel = RegionSelector(self)
        self.wait_window(sel)
        self.deiconify()
        if sel.result:
            self.region_var.set(",".join(str(c) for c in sel.result))
            self.log(f"Região definida: {sel.result}")

    def _detect_color(self) -> None:
        region = self._parse_region()
        x1, y1, x2, y2 = region
        if x2 <= x1 or y2 <= y1:
            messagebox.showinfo("Cor", "Defina a região primeiro.")
            return
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        try:
            color = screen.sample_color(cx, cy)
        except Exception as exc:
            messagebox.showerror("Erro", f"Falha ao ler cor: {exc}")
            return
        self.pot_color.set(",".join(str(c) for c in color))
        self.log(f"Cor detectada no centro da região: {color}")

    def _test_read(self) -> None:
        pot = self._form_to_potion()
        if not (pot.region[2] > pot.region[0] and pot.region[3] > pot.region[1]):
            messagebox.showinfo("Teste", "Defina a região primeiro.")
            return
        try:
            frac = screen.health_fraction(pot.region, pot.color, pot.tolerance)
        except Exception as exc:
            messagebox.showerror("Erro", f"Falha na leitura: {exc}")
            return
        self.log(f"Leitura de vida atual: {frac:.0%} (dispara abaixo de {pot.threshold_pct:.0%})")

    # --- hotkey + controle -------------------------------------------------

    def _apply_hotkey(self) -> None:
        hk = self.hotkey_var.get().strip().lower() or "f8"
        if not self.hotkeys.available:
            self.log("[!] lib 'keyboard' indisponível — hotkey global desativada")
            return
        ok = self.hotkeys.register(hk, self._hotkey_fired)
        self.log(f"Hotkey '{hk}' {'registrada' if ok else 'FALHOU'}")

    def _hotkey_fired(self) -> None:
        # Chamado pela thread do `keyboard`; volta para a thread da UI.
        self.after(0, self._toggle)

    def _toggle(self) -> None:
        profile = self._form_to_profile()
        self.engine.toggle(profile)
        self._refresh_status()

    def _refresh_status(self) -> None:
        running = self.engine.running
        if running:
            self.toggle_btn.config(text="■ Parar (ON)")
            self.status_lbl.config(text="RODANDO", foreground="green")
        else:
            self.toggle_btn.config(text="▶ Iniciar (OFF)")
            self.status_lbl.config(text="parado", foreground="gray")
        if self.overlay is not None:
            self.overlay.update_state(running, self.engine.last_health)
        self.after(400, self._refresh_status)

    # --- opções + pânico ---------------------------------------------------

    def _apply_settings(self) -> None:
        """Aplica as configurações: overlay e tecla de pânico."""
        # Overlay
        if self.settings.overlay_enabled and self.overlay is None:
            self.overlay = StatusOverlay(self)
        elif not self.settings.overlay_enabled and self.overlay is not None:
            self.overlay.destroy()
            self.overlay = None

        # Tecla de pânico (precisa diferir da hotkey de liga/desliga)
        panic = self.settings.panic_key.strip().lower()
        toggle = self.hotkey_var.get().strip().lower() if hasattr(self, "hotkey_var") else ""
        if panic and panic != toggle and self.panic_hotkeys.available:
            ok = self.panic_hotkeys.register(panic, self._panic_fired)
            self.log(f"Tecla de pânico '{panic}' {'registrada' if ok else 'FALHOU'}")
        else:
            self.panic_hotkeys.unregister()
            if panic and panic == toggle:
                self.log("[!] tecla de pânico igual à de liga/desliga — ignorada")

    def _panic_fired(self) -> None:
        self.after(0, self._panic)

    def _panic(self) -> None:
        self.engine.stop()
        self._refresh_status()
        self.log("[PÂNICO] tudo parado")

    def _open_options(self) -> None:
        OptionsDialog(self)

    # --- auto-update -------------------------------------------------------

    def _check_update_async(self) -> None:
        threading.Thread(target=self._check_update_worker, daemon=True).start()

    def _check_update_worker(self) -> None:
        info = updater.check_for_update()
        self.after(0, lambda: self._on_update_result(info))

    def _on_update_result(self, info: "updater.UpdateInfo | None") -> None:
        if info is None:
            self.log("Você está na versão mais recente.")
            return
        self._pending_update = info
        self.update_lbl.config(text=f"Nova versão disponível: v{info.version}")
        self.update_bar.pack(fill="x", padx=8, pady=(0, 4))
        self.log(f"Atualização encontrada: v{info.version}")

    def _apply_update(self) -> None:
        info = self._pending_update
        if not info:
            return
        if not info.download_url:
            webbrowser.open(info.release_url)
            return
        if not messagebox.askyesno(
            "Atualizar",
            f"Baixar e instalar a v{info.version} agora?\nO Praxis será fechado.",
        ):
            return
        self.log("Baixando atualização...")
        if updater.download_and_run(info.download_url, info.sha256_url):
            self._on_close()
        else:
            messagebox.showerror(
                "Atualização",
                "Falha ao baixar ou verificar a integridade. Abrindo a página do release.",
            )
            webbrowser.open(info.release_url)

    # --- log + ciclo de vida ----------------------------------------------

    def log(self, msg: str) -> None:
        line = time.strftime("%H:%M:%S ") + msg

        def _append() -> None:
            self.log_text.config(state="normal")
            self.log_text.insert("end", line + "\n")
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.after(0, _append)

        if getattr(self, "settings", None) and self.settings.log_to_file:
            try:
                path = config.PROFILES_DIR.parent / "praxis.log"
                with path.open("a", encoding="utf-8") as fh:
                    fh.write(time.strftime("%Y-%m-%d ") + line + "\n")
            except Exception:
                pass

    def _on_close(self) -> None:
        self.engine.stop()
        self.hotkeys.unregister()
        self.panic_hotkeys.unregister()
        if self.overlay is not None:
            self.overlay.destroy()
        self.destroy()


def run() -> None:
    config.seed_defaults()
    app = MacroApp()
    app.mainloop()
