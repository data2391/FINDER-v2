import queue, threading, json, asyncio, uuid
from flask import Flask, request, jsonify, render_template, Response, stream_with_context
from scraper import run_search

app = Flask(__name__, template_folder="templates", static_folder="static")

_sessions = {}   # sid -> {queue, captcha_event}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/search/start")
def search_start():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "Requête vide."})
    sid = uuid.uuid4().hex[:10]
    eq  = queue.Queue()
    ce  = threading.Event()
    _sessions[sid] = {"queue": eq, "captcha_event": ce}

    def run():
        asyncio.run(run_search(q, eq.put, ce))

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"sid": sid})

@app.route("/events/<sid>")
def events(sid):
    s = _sessions.get(sid)
    if not s:
        return jsonify({"error": "Session inconnue."}), 404

    def stream():
        while True:
            try:
                evt = s["queue"].get(timeout=40)
                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
                if evt.get("type") == "complete":
                    break
            except queue.Empty:
                yield 'data: {"type":"ping"}\n\n'

    return Response(
        stream_with_context(stream()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"}
    )

@app.route("/captcha/ack/<sid>", methods=["POST"])
def captcha_ack(sid):
    s = _sessions.get(sid)
    if s:
        s["captcha_event"].set()
    return jsonify({"ok": True})

if __name__ == "__main__":
    print("\n🚀  FINDER v2.0 — http://localhost:8000\n")
    app.run(host="0.0.0.0", port=8000, debug=False, threaded=True)
