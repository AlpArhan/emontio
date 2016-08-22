from flask import Flask, render_template, request, redirect
from templates.emontio_main_web import *
from templates.emontio_main_web import main
import cf_deployment_tracker
import os


cf_deployment_tracker.track()
app = Flask(__name__)
port = int(os.getenv('VCAP_APP_PORT', 8080))


@app.route("/")
def main_web():
    return render_template('index.html')

@app.route("/emontio_main_web.py", methods = ['POST'])
def run_emontio():
    stock_id = request.form['stock_id']
    stock_name = request.form['stock_name']
    web_url = request.form['web_url']

    if not stock_id or not stock_name or not web_url:
        return render_template('index.html' , stock_id=stock_id, stock_name=stock_name, web_url=web_url)

    else:
        if "www." not in web_url:
            web_url ="www." + web_url
        if not web_url.endswith(".com") == True:
            web_url = web_url + ".com"
        if not web_url.startswith("http://") == True:
            web_url = "http://" + web_url

        #execute the python script.
        analyzer = handle_form_submit(stock_id, stock_name, web_url)

        return render_template('emontio_output.html',
            scan_web=analyzer.result_scan_web,
            tone_analysis=analyzer.results_tone_analyzer,
            sentiment_analysis=analyzer.result_sentiment_analysis)


if __name__ == "__main__":
  app.run(debug = True, port=port)
