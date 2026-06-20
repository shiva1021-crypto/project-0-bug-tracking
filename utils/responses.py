from flask import flash, jsonify, redirect, request, url_for


def is_ajax_request():
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def action_response(message, endpoint, status=200, category="success", **values):
    if is_ajax_request():
        payload = {"ok": status < 400}
        payload["message" if status < 400 else "error"] = message
        return jsonify(payload), status

    flash(message, category)
    return redirect(url_for(endpoint, **values))
