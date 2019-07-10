from base import create_app


app = create_app("copernicus.cfg")

if __name__ == "__main__":
    app.run(debug=True, use_debugger=False, use_reloader=False,
            passthrough_errors=True)
