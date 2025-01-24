from flask import Flask, render_template, request
import subprocess
import socket, psutil
import speedtest,time
import os, requests


app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ping', methods=['GET', 'POST'])
def ping():
    result = None
    if request.method == 'POST':
        ip = request.form.get('ip')
        try:
            # Adjust command based on OS
            if os.name == 'nt':  # Windows
                command = ['ping', '-n', '4', ip]
            else:  # Linux/Mac
                command = ['ping', '-c', '4', ip]
                
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
            )
            output = result.stdout
        except Exception as e:
            output = f"Error: {e}"
        return render_template('ping.html', ip=ip, result=output)
    return render_template('ping.html')

@app.route('/traceroute', methods=['GET', 'POST'])
def traceroute():
    result = None
    if request.method == 'POST':
        ip = request.form.get('ip')
        try:
            if os.name == 'nt':  # Windows
                command = ['tracert', ip]
            else:  
                command = ['traceroute', ip]
                
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
            )
            output = result.stdout
        except Exception as e:
            output = f"Error: {e}"
        return render_template('traceroute.html', ip=ip, result=output)
    return render_template('traceroute.html')


@app.route('/dns', methods=['GET', 'POST'])
def dns_lookup():
    result = None
    if request.method == 'POST':
        domain = request.form.get('domain')
        try:
            ip = socket.gethostbyname(domain)
            result = f"IP address of {domain} is {ip}"
        except Exception as e:
            result = f"Error: {e}"
        return render_template('dns.html', domain=domain, result=result)
    return render_template('dns.html')

@app.route('/speedtest')
def speed_test():
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        download_speed = st.download() / 1_000_000  # Convert to Mbps
        upload_speed = st.upload() / 1_000_000      # Convert to Mbps
        return render_template(
            'speedtest.html',
            download_speed=f"{download_speed:.2f}",
            upload_speed=f"{upload_speed:.2f}",
        )
    except Exception as e:
        return render_template('speedtest.html', error=f"Error: {e}")


@app.route('/geoip', methods=['GET', 'POST'])
def geoip_lookup():
    result = None
    if request.method == 'POST':
        ip = request.form.get('ip')
        try:
            response = requests.get(f"https://ipinfo.io/{ip}/json")
            result = response.json()
        except Exception as e:
            result = {"error": str(e)}
    return render_template('geoip.html', result=result)

# @app.route('/bandwidth')
# def bandwidth_monitor():
#     # Measure bandwidth usage for 2 seconds
#     stats_start = psutil.net_io_counters()
#     time.sleep(2)
#     stats_end = psutil.net_io_counters()
    
#     download_speed = (stats_end.bytes_recv - stats_start.bytes_recv) / (1024 * 1024 * 2)  # MBps
#     upload_speed = (stats_end.bytes_sent - stats_start.bytes_sent) / (1024 * 1024 * 2)    # MBps

#     return render_template('bandwidth.html', download_speed=download_speed, upload_speed=upload_speed)

@app.route('/dashboard', methods=['GET', 'POST'])
def network_dashboard():
    target = None
    latency, packet_loss, hops = [], 0, 0

    if request.method == 'POST':
        target = request.form.get('target')  # Get the user input
        latency, packet_loss = measure_ping(target)
        hops = measure_traceroute(target)
        print(hops)

    return render_template(
        'dashboard.html',
        target=target,
        latency=latency,
        packet_loss=packet_loss,
        hops=hops
    )

def measure_ping(target):
    """
    Run ping to measure latency and packet loss.
    Returns:
        - latency: List of response times in milliseconds
        - packet_loss: Percentage of packets lost
    """
    try:
        if os.name == 'nt':  # Windows
            command = ['ping', '-n', '4', target]
        else:  # Linux/Mac
            command = ['ping', '-c', '4', target]

        result = subprocess.run(command, capture_output=True, text=True)
        
        # Check if the command ran successfully
        if result.returncode != 0:
            print(f"Ping command failed with error:\n{result.stderr}")
            return [], 100  # Assume 100% packet loss if the command fails

        output = result.stdout
        print(f"Ping command output:\n{output}")  # Debugging purpose

        latency = []
        packet_loss = 0

        for line in output.splitlines():
            # Extract latency information
            if "time=" in line:  # Common in both Windows and Linux/Mac
                try:
                    time_part = line.split("time=")[-1]
                    time_ms = time_part.split()[0].strip("ms")
                    latency.append(float(time_ms))
                except ValueError:
                    pass  # Ignore lines that can't be parsed as latency

            # Extract packet loss information (Windows format)
            if os.name == 'nt' and "Lost" in line:
                try:
                    loss_str = line.split(",")[2].split()[0].replace('%', '')
                    packet_loss = float(loss_str)
                except (IndexError, ValueError):
                    pass

            # Extract packet loss information (Linux/Mac format)
            elif os.name != 'nt' and "loss" in line:
                try:
                    loss_str = line.split(",")[2].split("%")[0].strip()
                    packet_loss = float(loss_str)
                except (IndexError, ValueError):
                    pass

        # If no latency is captured, assume ping failed
        if not latency:
            latency = []

        return latency, packet_loss

    except Exception as e:
        print(f"Error in measure_ping: {e}")
        return [], 0


def measure_traceroute(target):
    """
    Run traceroute or tracert to count the number of hops.
    Returns:
        - hops: Number of hops to the target
    """
    try:
        if os.name == 'nt':  # Windows
            command = ['tracert', target]
        else:  # Linux/Mac
            command = ['traceroute', target]

        result = subprocess.run(command, capture_output=True, text=True)
        output = result.stdout

        print(f"Traceroute command output:\n{output}")  # Debugging purpose

        hops = 0
        for line in output.splitlines():
            # Windows: Look for the hop lines with IPs or domain names (usually in the form "1    <ms>    <ms>    <ms>  <IP>")
            if os.name == 'nt':
                if line.strip() and line[0].isdigit():  # Check if the line starts with a digit (indicating a hop)
                    hops += 1
            # Linux/Mac: Hop lines look like "1  192.168.1.1  0.392 ms  0.527 ms  0.712 ms"
            elif os.name != 'nt':
                if line.strip() and len(line.split()) > 1:  # Ensure the line has more than one part (hop details)
                    hops += 1

        return hops
    except Exception as e:
        print(f"Error in measure_traceroute: {e}")
        return 0



if __name__ == '__main__':
    app.run(debug=True)
