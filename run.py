from base import create_app


if __name__ == "__main__":

    app = create_app("copernicus.cfg")
    app.run(debug=True, use_debugger=False, use_reloader=False,
            passthrough_errors=True)
