import logging
from flask import Flask, jsonify, render_template_string, send_from_directory

from .config import RECORDINGS_DIR
from .storage import list_recent_transcripts


HTML = """
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>Field Notes Device</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 2rem;
            max-width: 1000px;
        }
        .page-meta {
            color: #666;
            margin-bottom: 1rem;
        }
        .note {
            border: 1px solid #ccc;
            padding: 1rem;
            margin-bottom: 1rem;
            border-radius: 8px;
        }
        .note-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 1rem;
        }
        .note-main {
            flex: 1;
            min-width: 0;
        }
        .meta {
            color: #666;
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
        }
        .transcript-row {
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
            margin-bottom: 0.75rem;
        }
        .transcript-actions {
            flex-shrink: 0;
        }
        .transcript-text {
            flex: 1;
            min-width: 0;
        }
        .audio-row {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-top: 0.5rem;
            flex-wrap: wrap;
        }
        .audio-actions {
            flex-shrink: 0;
        }
        .details,
        .deep-dive {
            display: none;
            margin-top: 0.75rem;
            padding: 0.75rem;
            background: #f7f7f7;
            border-radius: 6px;
        }
        .deep-dive pre {
            margin: 0;
            white-space: pre-wrap;
            word-wrap: break-word;
            font-size: 0.85rem;
            overflow-x: auto;
        }
        .button-row {
            display: flex;
            gap: 0.5rem;
            align-items: flex-start;
            flex-shrink: 0;
        }
        button,
        .download-btn {
            padding: 0.4rem 0.8rem;
            cursor: pointer;
            flex-shrink: 0;
            font-size: 0.95rem;
            border: 1px solid #aaa;
            background: #f5f5f5;
            border-radius: 6px;
            text-decoration: none;
            color: #222;
            display: inline-block;
        }
        button:hover,
        .download-btn:hover {
            background: #ececec;
        }
        pre.transcript {
            white-space: pre-wrap;
            word-wrap: break-word;
            margin: 0;
        }
        .badge {
            padding: 0.15rem 0.45rem;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: bold;
        }
        .high { background: #dff5e1; color: #1f6b2a; }
        .medium { background: #fff4d6; color: #8a6700; }
        .low { background: #fde2e2; color: #9b1c1c; }
        .unknown { background: #ececec; color: #555; }
        .copy-status {
            font-size: 0.9rem;
            color: #2f6f44;
            margin-top: 0.35rem;
        }
        .sr-only {
            position: absolute;
            left: -9999px;
            top: auto;
            width: 1px;
            height: 1px;
            overflow: hidden;
        }
        .audio-duration {
            color: #666;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <h1>Field Technician Notes</h1>
    <div class="page-meta">Auto-refreshing list every 5 seconds without reloading the page.</div>
    <div id="notes-container"></div>

    <script>
        const initialNotes = {{ notes | tojson }};
        let refreshInFlight = false;
        let lastNotesSignature = "";

        function escapeHtml(value) {
            if (value === null || value === undefined) return "";
            return String(value)
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#39;");
        }

        function confidenceBadge(confidence) {
            if (confidence === null || confidence === undefined) {
                return 'unknown <span class="badge unknown">Unknown</span>';
            }

            const num = Number(confidence);
            const label = num >= 0.9 ? "High" : (num >= 0.75 ? "Medium" : "Low");
            const klass = num >= 0.9 ? "high" : (num >= 0.75 ? "medium" : "low");

            return `${num.toFixed(2)} <span class="badge ${klass}">${label}</span>`;
        }

        function noteId(note, idx) {
            return (note.audio_filename || note.created_at || ("note-" + idx))
                .replace(/[^A-Za-z0-9_.-]/g, "_");
        }

        function detailsKey(id) {
            return "details-" + id;
        }

        function deepDiveKey(id) {
            return "deep-" + id;
        }

        function buildNotesSignature(notes) {
            return JSON.stringify(
                (notes || []).map(note => ({
                    created_at: note.created_at,
                    audio_filename: note.audio_filename,
                    transcript: note.transcript,
                    processing_time_seconds: note.processing_time_seconds,
                    duration_seconds: note.duration_seconds,
                    confidence: note.confidence,
                    language: note.language,
                    model: note.model
                }))
            );
        }

        function toggleSectionById(elementId, storageKey, btn, showText, hideText) {
            const el = document.getElementById(elementId);
            if (!el) return;

            const open = el.style.display === "block";
            if (open) {
                el.style.display = "none";
                btn.textContent = showText;
                localStorage.removeItem(storageKey);
            } else {
                el.style.display = "block";
                btn.textContent = hideText;
                localStorage.setItem(storageKey, "open");
            }
        }

        function toggleDetails(id, btn) {
            toggleSectionById("details-panel-" + id, detailsKey(id), btn, "Show Details", "Hide Details");
        }

        function toggleDeepDive(id, btn) {
            toggleSectionById("deep-panel-" + id, deepDiveKey(id), btn, "Deep Dive", "Hide Deep Dive");
        }

        async function copyTranscript(textareaId, statusId) {
            const textarea = document.getElementById(textareaId);
            const status = document.getElementById(statusId);
            if (!textarea || !status) return;

            const text = textarea.value;

            try {
                if (navigator.clipboard && window.isSecureContext) {
                    await navigator.clipboard.writeText(text);
                } else {
                    textarea.classList.remove("sr-only");
                    textarea.select();
                    textarea.setSelectionRange(0, textarea.value.length);
                    document.execCommand("copy");
                    textarea.classList.add("sr-only");
                }

                status.textContent = "Copied!";
                setTimeout(() => {
                    if (status.textContent === "Copied!") {
                        status.textContent = "";
                    }
                }, 1500);
            } catch (err) {
                status.textContent = "Copy failed";
                setTimeout(() => {
                    if (status.textContent === "Copy failed") {
                        status.textContent = "";
                    }
                }, 1500);
            }
        }

        function onAudioMetadataLoaded(audioEl, durationId) {
            const target = document.getElementById(durationId);
            if (!target || !audioEl) return;

            if (!isNaN(audioEl.duration) && isFinite(audioEl.duration)) {
                target.textContent = `Duration: ${audioEl.duration.toFixed(2)} sec`;
            }
        }

        function renderNotes(notes) {
            const container = document.getElementById("notes-container");
            if (!container) return;

            if (!notes || notes.length === 0) {
                container.innerHTML = "<p>No transcripts yet.</p>";
                return;
            }

            const html = notes.map((note, idx) => {
                const id = noteId(note, idx);
                const transcript = note.transcript || "";
                const transcriptEscaped = escapeHtml(transcript);
                const prettyJson = escapeHtml(JSON.stringify(note.deepgram_result || {}, null, 2));
                const audioFilename = note.audio_filename ? escapeHtml(note.audio_filename) : "";
                const createdAt = escapeHtml(note.created_at || "");
                const model = escapeHtml(note.model || "unknown");
                const language = escapeHtml(note.language || "unknown");
                const jsonFile = escapeHtml(note._file || "");
                const durationSeconds = note.duration_seconds ?? "unknown";
                const processingTime = note.processing_time_seconds ?? "unknown";

                const detailsOpen = localStorage.getItem(detailsKey(id)) === "open";
                const deepOpen = localStorage.getItem(deepDiveKey(id)) === "open";

                return `
                    <div class="note">
                        <div class="note-header">
                            <div class="note-main">
                                <div class="meta">
                                    <strong>${createdAt}</strong><br>
                                    ${audioFilename}
                                </div>

                                <div class="transcript-row">
                                    <div class="transcript-actions">
                                        <button type="button" onclick="copyTranscript('transcript-${id}', 'copy-${id}')">Copy</button>
                                        <div id="copy-${id}" class="copy-status"></div>
                                    </div>

                                    <div class="transcript-text">
                                        <pre class="transcript">${transcriptEscaped}</pre>
                                    </div>
                                </div>

                                <textarea id="transcript-${id}" class="sr-only">${transcript}</textarea>

                                ${audioFilename ? `
                                    <div class="audio-row">
                                        <div class="audio-actions">
                                            <a class="download-btn" href="/audio/${audioFilename}" download="${audioFilename}">Download</a>
                                        </div>
                                        <audio controls preload="metadata" onloadedmetadata="onAudioMetadataLoaded(this, 'audio-duration-${id}')">
                                            <source src="/audio/${audioFilename}" type="audio/wav">
                                            Your browser does not support audio playback.
                                        </audio>
                                        <div class="audio-duration" id="audio-duration-${id}">
                                            Duration: loading...
                                        </div>
                                    </div>
                                ` : ""}

                            </div>

                            <div class="button-row">
                                <button type="button" onclick="toggleDetails('${id}', this)">${detailsOpen ? "Hide Details" : "Show Details"}</button>
                                <button type="button" onclick="toggleDeepDive('${id}', this)">${deepOpen ? "Hide Deep Dive" : "Deep Dive"}</button>
                            </div>
                        </div>

                        <div class="details" id="details-panel-${id}" style="display:${detailsOpen ? "block" : "none"};">
                            <div><b>Model:</b> ${model}</div>
                            <div><b>Confidence:</b> ${confidenceBadge(note.confidence)}</div>
                            <div><b>Duration:</b> ${durationSeconds} sec</div>
                            <div><b>Processing Time:</b> ${processingTime} sec</div>
                            <div><b>Language:</b> ${language}</div>
                            <div><b>JSON File:</b> ${jsonFile}</div>
                        </div>

                        <div class="deep-dive" id="deep-panel-${id}" style="display:${deepOpen ? "block" : "none"};">
                            <pre>${prettyJson}</pre>
                        </div>
                    </div>
                `;
            }).join("");

            container.innerHTML = html;
        }

        async function refreshNotes() {
            if (refreshInFlight) return;
            refreshInFlight = true;

            try {
                const response = await fetch("/api/transcripts", { cache: "no-store" });
                if (!response.ok) return;

                const notes = await response.json();
                const newSignature = buildNotesSignature(notes);

                if (newSignature !== lastNotesSignature) {
                    renderNotes(notes);
                    lastNotesSignature = newSignature;
                }
            } catch (err) {
                console.error("Refresh failed", err);
            } finally {
                refreshInFlight = false;
            }
        }

        renderNotes(initialNotes);
        lastNotesSignature = buildNotesSignature(initialNotes);
        setInterval(refreshNotes, 5000);
    </script>
</body>
</html>
"""


def create_app():
    app = Flask(__name__)

    @app.route("/")
    def index():
        notes = list_recent_transcripts(limit=20)
        return render_template_string(HTML, notes=notes)

    @app.route("/audio/<path:filename>")
    def audio(filename):
        return send_from_directory(RECORDINGS_DIR, filename, as_attachment=False)

    @app.route("/api/transcripts")
    def api():
        return jsonify(list_recent_transcripts(limit=20))

    return app


def run_web():
    app = create_app()

    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)

    app.run(host="0.0.0.0", port=5000)
