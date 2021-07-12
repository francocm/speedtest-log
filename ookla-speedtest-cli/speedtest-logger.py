import json, logging, os, psutil, subprocess, sys

from ischedule import schedule, run_loop
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from os import environ

def create_logger() :
    log = logging.getLogger('')
    log.setLevel(logging.INFO)
    format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(format)
    log.addHandler(ch)
    return log

log = create_logger()

pid = os.getpid()

influx_url = "http://influxdb:8086"
influx_org = environ.get('DOCKER_INFLUXDB_INIT_ORG')
influx_bucket = environ.get('DOCKER_INFLUXDB_INIT_BUCKET')
influx_token = environ.get('DOCKER_INFLUXDB_INIT_ADMIN_TOKEN')

speedtest_server = environ.get('SPEEDTEST_SERVER')
speedtest_interval_mins = float(environ.get('SPEEDTEST_INTERVAL_MINUTES'))
speedtest_interval_seconds = speedtest_interval_mins * 60

log.info("Initialising speedtest-logger on PID %s ..." % pid)
log.info("Speed Test poll interval set to %s minutes (%s seconds)." % (speedtest_interval_mins, speedtest_interval_seconds))
if speedtest_server:
    speedtest_server = int(speedtest_server)
    log.info("Using custom speedtest server: %s" % speedtest_server)
else:
    log.info("Using random speedtest server.")
log.info("Influx DB URL [%s], org [%s], bucket [%s]." % (influx_url, influx_org, influx_bucket))

def die():
    log.fatal("Dying.")
    thisApp = psutil.Process(pid)
    thisApp.terminate()

def build_speedtest_command():
    cmd = ""
    if speedtest_server:
        cmd = "speedtest-cli --json --server %s" % speedtest_server
    else:
        cmd = "speedtest-cli --json"
    return cmd.split(" ")

def save_speedtest_results(speedtest_results):
    influx_client = InfluxDBClient(url=influx_url, token=influx_token, org=influx_org)
    influx_write_api = influx_client.write_api(write_options=SYNCHRONOUS)
    record = Point("speedtest") \
        .tag("server_id", int(speedtest_results['server']['id'])) \
        .tag("server_name", speedtest_results['server']['sponsor']) \
        .tag("server_country_name", speedtest_results['server']['country']) \
        .field("server_distance", float(speedtest_results['server']['d'])) \
        .field("ping", float(speedtest_results['ping'])) \
        .field("download_speed_mbps", float(speedtest_results['download'] / 1024 / 1024)) \
        .field("upload_speed_mbps", float(speedtest_results['upload'] / 1024 / 1024)) \
        .field("bytes_received", int(speedtest_results['bytes_received'])) \
        .field("bytes_sent", int(speedtest_results['bytes_sent'])) \
        .field("client_ip", speedtest_results['client']['ip']) \
        .field("client_isp", speedtest_results['client']['isp']) \
        .field("client_country_code", speedtest_results['client']['country'])
    influx_write_api.write(bucket=influx_bucket, record=record)
    influx_write_api.close()
    influx_client.close()
    log.info("Speedtest persisted to Influx DB.")

def run_speedtest():
    cmd = build_speedtest_command()
    log.info("Running speedtest using command: %s" % cmd)
    speedtest_output = subprocess.run(cmd, capture_output=True)
    if speedtest_output.returncode != 0:
        log.error("Speedtest failed! Details: %s" % speedtest_output)
        die()
    json_output = speedtest_output.stdout.decode()
    log.debug("Received output: %s" % json_output)
    speedtest_data = json.loads(json_output)
    save_speedtest_results(speedtest_data)

run_speedtest()
schedule(run_speedtest, interval=speedtest_interval_seconds)

run_loop()
