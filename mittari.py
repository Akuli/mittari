import re
import time


def grep_ints(regex, path):
    with open(path, 'r') as file:
        for line in file:
            m = re.search(regex, line)
            if m is not None:
                return [int(value) for value in m.groups()]

    raise ValueError(f"regex {regex!r} not found in contents of {path!r}")


last_total_since_boot = None
last_idle_since_boot = None


# Returns between 0.0 and 1.0. Based on psutils source code.
def get_cpu_usage() -> float:
    global last_total_since_boot
    global last_idle_since_boot

    # Ignore last 2 fields, similar to psutils library.
    # psutils has comments saying that htop does this too.
    first_5_fields = grep_ints(r'^cpu +(\d+) +(\d+) +(\d+) +(\d+) +(\d+)', '/proc/stat')

    # https://www.linuxhowtos.org/System/procstat.htm
    total_since_boot = sum(first_5_fields)
    idle_since_boot = int(first_5_fields[3]) + int(first_5_fields[4])  # idle + iowait

    if last_total_since_boot is None or last_total_since_boot == total_since_boot:
        result = 0.0
    else:
        total = total_since_boot - last_total_since_boot
        idle = idle_since_boot - last_idle_since_boot
        result = (total - idle) / total

    last_total_since_boot = total_since_boot
    last_idle_since_boot = idle_since_boot

    return result


# Returns between 0.0 and 1.0.
def get_mem_usage() -> float:
    total = grep_ints(r'MemTotal:\s+(\d+)\s+kB', '/proc/meminfo')[0]
    available = grep_ints(r'MemAvailable:\s+(\d+)\s+kB', '/proc/meminfo')[0]
    return (total - available)/total


#while True:
#    print("%.2f %.2f" % (get_cpu_usage(), get_mem_usage()))
#    time.sleep(0.1)

while True:
    print('|' + ('x' * round(get_cpu_usage()*75)).ljust(75) + '|')
    time.sleep(0.1)
