import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import {Slider} from 'resource:///org/gnome/shell/ui/slider.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const LAMP = GLib.find_program_in_path('lamp') ?? GLib.build_filenamev([GLib.get_home_dir(), '.local', 'bin', 'lamp']);
const STATE_FILE = GLib.build_filenamev([GLib.get_user_config_dir(), 'tuya-beacon-linux', 'state.json']);
const DEBOUNCE_MS = 300;

const PRESETS = [
    ['red', '#ff3b30'], ['orange', '#ff9500'], ['yellow', '#ffcc00'],
    ['green', '#34c759'], ['cyan', '#32ade6'], ['blue', '#1a6dff'],
    ['purple', '#9b4dff'], ['pink', '#ff4fa3'],
];

function lamp(...args) {
    try {
        Gio.Subprocess.new([LAMP, ...args],
            Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_SILENCE);
    } catch (e) {
        logError(e, 'tuya-beacon');
    }
}

function readState() {
    try {
        const [ok, bytes] = Gio.File.new_for_path(STATE_FILE).load_contents(null);
        if (ok)
            return JSON.parse(new TextDecoder().decode(bytes));
    } catch (e) {
        // no state yet
    }
    return null;
}

const LampIndicator = GObject.registerClass(
class LampIndicator extends PanelMenu.Button {
    _init() {
        super._init(0.5, 'Tuya Beacon lamp');
        this._mode = 'white';
        this._syncing = false;
        this.add_child(new St.Icon({
            icon_name: 'display-brightness-symbolic',
            style_class: 'system-status-icon',
        }));

        this._sw = new PopupMenu.PopupSwitchMenuItem('Lamp', true);
        this._sw.connect('toggled', (_i, state) => lamp(state ? 'on' : 'off'));
        this.menu.addMenuItem(this._sw);
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        this._bright = this._makeSlider('Brightness', 1.0, pct => lamp('bright', String(pct)));
        this._temp = this._makeSlider('White', 0.5, pct => {
            this._setMode('white');
            lamp('temp', String(pct));
        });
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        const row = new PopupMenu.PopupBaseMenuItem({reactive: false, can_focus: false});
        const box = new St.BoxLayout({x_expand: true, style: 'spacing: 10px; padding: 4px 6px;'});
        for (const [cmd, hex] of PRESETS) {
            const b = new St.Button({style_class: 'lamp-swatch', style: `background-color: ${hex};`, can_focus: true});
            b.connect('clicked', () => {
                this._setMode('color');
                lamp('color', cmd);
                return false;
            });
            box.add_child(b);
        }
        row.add_child(box);
        this.menu.addMenuItem(row);

        // on open, read the last state the daemon saved and move the controls to it
        this.menu.connect('open-state-changed', (_m, open) => {
            if (open)
                this._syncFromState();
        });
        this._setMode('white');
    }

    _syncFromState() {
        const s = readState();
        if (!s)
            return;
        this._syncing = true;
        try {
            if (typeof s.bright === 'number')
                this._bright.slider.value = Math.max(0, Math.min(1, s.bright / 100));
            if (typeof s.temp === 'number')
                this._temp.slider.value = Math.max(0, Math.min(1, s.temp / 100));
            if (typeof s.on === 'boolean')
                this._sw.setToggleState(s.on);
            this._setMode(s.mode === 'color' ? 'color' : 'white');
        } finally {
            this._syncing = false;
        }
    }

    _setMode(mode) {
        this._mode = mode;
        if (this._temp)
            this._temp.item.opacity = (mode === 'color') ? 80 : 255;
    }

    _makeSlider(label, initial, onChange) {
        const item = new PopupMenu.PopupBaseMenuItem({activate: false});
        item.add_child(new St.Label({text: label, style: 'min-width: 80px;'}));
        const slider = new Slider(initial);
        slider.x_expand = true;
        const val = new St.Label({text: `${Math.round(initial * 100)}%`,
            style: 'min-width: 42px; text-align: right;'});
        let tid = 0;
        slider.connect('notify::value', () => {
            val.text = `${Math.round(slider.value * 100)}%`;
            if (this._syncing)
                return;                       // syncing: update the label only, do not send
            if (tid)
                GLib.source_remove(tid);
            tid = GLib.timeout_add(GLib.PRIORITY_DEFAULT, DEBOUNCE_MS, () => {
                tid = 0;
                onChange(Math.max(1, Math.round(slider.value * 100)));
                return GLib.SOURCE_REMOVE;
            });
        });
        item.add_child(slider);
        item.add_child(val);
        this.menu.addMenuItem(item);
        return {item, slider, val};
    }
});

export default class TuyaBeaconExtension extends Extension {
    enable() {
        this._indicator = new LampIndicator();
        Main.panel.addToStatusArea('tuya-beacon', this._indicator);
    }

    disable() {
        this._indicator?.destroy();
        this._indicator = null;
    }
}
