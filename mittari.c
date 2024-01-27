#define _POSIX_C_SOURCE 200809L

#include <assert.h>
#include <math.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <time.h>
#include <spawn.h>
#include <errno.h>
#include <unistd.h>
#include <signal.h>
#include <sys/wait.h>

#define show_warning(...) ( fprintf(stderr, "Warning: "), fprintf(stderr, __VA_ARGS__), fprintf(stderr, "\n") )
#define fail(...) ( fprintf(stderr, "Error: "),   fprintf(stderr, __VA_ARGS__), fprintf(stderr, "\n"), exit(1) )

static struct CpuStats {
    long long total_since_boot;
    long long idle_since_boot;
} last_cpu_stats = {-1,-1};


/* Returns the cpu usage as a fraction between 0 and 1.

Return value is the average since the last time this function was called.

Somewhat similar to source code of Python's psutil library.
*/
static float get_cpu_usage(void)
{
    FILE *f = fopen("/proc/stat", "r");
    if (!f) {
        show_warning("failed to open /proc/stat: %s", strerror(errno));
        return 0;
    }

    // https://www.linuxhowtos.org/System/procstat.htm
    long long user_field, nice_field, system_field, idle_field, iowait_field;
    char line[4096];
    bool found = false;
    while (fgets(line, sizeof(line), f)) {
        if (sscanf(line, "cpu %lld %lld %lld %lld %lld", &user_field, &nice_field, &system_field, &idle_field, &iowait_field) == 5) {
            found = true;
            break;
        }
    }
    fclose(f);

    if (!found) {
        show_warning("failed to find 'cpu ' line in /proc/stat");
        return 0;
    }

    struct CpuStats prev = last_cpu_stats;
    struct CpuStats cur = {
        .total_since_boot = user_field+nice_field+system_field+idle_field+iowait_field,
        .idle_since_boot = idle_field+iowait_field,
    };
    last_cpu_stats = cur;

    if (prev.total_since_boot == -1 || prev.total_since_boot == cur.total_since_boot) {
        return 0;
    }

    // Compute average CPU usage since the last time this was called
    long long total = cur.total_since_boot - prev.total_since_boot;
    long long idle = cur.idle_since_boot - prev.idle_since_boot;
    return (total - idle) / (float)total;
}

/*
Returns RAM usage as a fraction between 0 and 1.

Counts file system cache and other such things as "free" because it will be used for other
stuff as needed. In other words, we look at what linux calls "available", not "free".
*/
static float get_ram_usage(void)
{
    FILE *f = fopen("/proc/meminfo", "r");
    if (!f) {
        show_warning("failed to open /proc/meminfo: %s", strerror(errno));
        return 0;
    }

    long long total = -1, available = -1;
    char line[4096];
    while (fgets(line, sizeof(line), f)) {
        sscanf(line, "MemTotal: %lld kB", &total);
        sscanf(line, "MemAvailable: %lld kB", &available);
    }
    fclose(f);

    if (total == -1 || available == -1) {
        show_warning("failed to parse /proc/meminfo");
        return 0;
    }

    return (total - available) / (float)total;
}


static const struct {
    const char *name;
    float (*func)(void);
} all_metrics[] = {
    { "CPU", get_cpu_usage },
    { "RAM", get_ram_usage },
};


struct ChannelConfig {
    float calibration[11];  // audio volumes for 0%, 10%, 20%, ..., 100%
    float (*metric)(void);
};

struct Config {
    char audio_device[100];
    int sample_rate;
    int frequency;
    float refresh_interval;
    struct ChannelConfig channels[2];
};

static void trim_whitespace(char *s)
{
    char *p = s;
    while (*p != '\0' && isspace(*p)) {
        p++;
    }
    memmove(s, p, strlen(p) + 1);

    p = &s[strlen(s)];
    while (p > s && isspace(p[-1])) {
        p--;
    }
    *p = '\0';
}

static bool strip_quotes(char *str)
{
    int n = strlen(str);
    if (n >= 2 && str[0] == '"' && str[n-1] == '"') {
        memmove(&str[0], &str[1], n-2);
        str[n-2] = '\0';
        return true;
    } else {
        return false;
    }
}

// returns error message, or NULL for success
static const char *parse_list_of_floats(const char *str, float *dest, int len)
{
    if (str[0] != '[') {
        return "list must start with '['";
    }
    str++;

    for (int i = 0; i < len; i++) {
        if (i > 0) {
            if (*str != ',') {
                return "missing ','";
            }
            str++;
        }

        char *end = NULL;
        dest[i] = strtod(str, &end);
        assert(end != NULL);
        str += end-str;
    }

    if (strcmp(str, "]")) {
        return "list must end with '['";
    }

    return NULL;
}

static void read_config_file(const char *path, struct Config *conf)
{
    memset(conf, 0, sizeof(*conf));

    FILE *f = fopen(path, "r");
    if (!f) {
        // TODO: test
        fail("cannot read config file \"%s\"", path);
        exit(1);
    }

    struct ChannelConfig *current_channel = NULL;

    int lineno = 0;
    char line[1024];
    while (fgets(line, sizeof(line), f)) {
        lineno++;

        if (strstr(line, "#")) {
            *strstr(line, "#") = '\0';
        }

        bool indent = isspace(line[0]);
        trim_whitespace(line);
        if (!line[0])
            continue;

        if (indent && !current_channel) {
            // TODO: test
            fail("config file \"%s\", line %d: unexpected indentation", path, lineno);
        }
        if (!indent && current_channel) {
            // end of indentation
            current_channel = NULL;
        }

        if (!indent && !strcmp(line, "left:")) {
            current_channel = &conf->channels[0];
            continue;
        }
        if (!indent && !strcmp(line, "right:")) {
            current_channel = &conf->channels[1];
            continue;
        }

        char *eq = strstr(line, "=");
        if (!eq) {
            // TODO: test
            fail("config file \"%s\", line %d: invalid syntax", path, lineno);
        }

        *eq = '\0';
        char *key = line;
        char *value = eq+1;
        trim_whitespace(key);
        trim_whitespace(value);

        if (!current_channel && !strcmp(key, "audio_device")) {
            strip_quotes(value);
            if (strlen(value) >= sizeof(conf->audio_device)) {
                // TODO: test
                fail("config file \"%s\", line %d: audio_device is too long", path, lineno);
            }
            strcpy(conf->audio_device, value);
        } else if (!current_channel && !strcmp(key, "sample_rate")) {
            conf->sample_rate = atoi(value);
        } else if (!current_channel && !strcmp(key, "frequency")) {
            conf->frequency = atoi(value);
        } else if (!current_channel && !strcmp(key, "refresh_interval")) {
            conf->refresh_interval = atof(value);
        } else if (current_channel && !strcmp(key, "calibration")) {
            const char *err = parse_list_of_floats(value, current_channel->calibration, sizeof(current_channel->calibration) / sizeof(current_channel->calibration[0]));
            if (err) {
                fail("config file \"%s\", line %d: %s", path, lineno, err);
            }
        } else if (current_channel && !strcmp(key, "metric")) {
            strip_quotes(value);
            bool found = false;
            for (unsigned i = 0; i < sizeof(all_metrics)/sizeof(all_metrics[0]); i++) {
                if (!strcmp(value, all_metrics[i].name)) {
                    current_channel->metric = all_metrics[i].func;
                    found = true;
                    break;
                }
            }
            if (!found) {
                fail("config file \"%s\", line %d: metric '%s' not found", path, lineno, value);
            }
        } else {
            show_warning("config file contains an unknown setting '%s' on line %d", key, lineno);
        }
    }

    fclose(f);

    // TODO: test
    #define CheckMissing(Val, Name) do{ if (!(Val)) { fail("config file \"%s\" is missing %s", path, (Name)); } } while(0)
        CheckMissing(conf->audio_device[0], "audio_device");
        CheckMissing(conf->sample_rate, "sample_rate");
        CheckMissing(conf->frequency, "frequency");
        CheckMissing(conf->refresh_interval, "refresh_interval");

        // Check last calibration value, because it cannot reasonably be zero
        int n = sizeof(conf->channels[0].calibration) / sizeof(conf->channels[0].calibration[0]);
        CheckMissing(conf->channels[0].calibration[n-1], "calibration");
        CheckMissing(conf->channels[1].calibration[n-1], "calibration");
    #undef CheckMissing
}


static float linear_map(float in_start, float in_end, float out_start, float out_end, float value)
{
    float slope = (out_end - out_start)/(in_end - in_start);
    return out_start + slope*(value - in_start);
}

static float get_gain(const struct ChannelConfig *cconf)
{
    float percentage = 100 * cconf->metric();
    assert(0 <= percentage && percentage <= 100);
    assert(sizeof(cconf->calibration) / sizeof(cconf->calibration[0]) == 11); // 0%, 10%, ..., 100%

    // Pick two known surrounding values (72% --> 70% and 80%)
    int index = (int)(percentage / 10);
    if (index == 10) {
        // Special case for 100%, take 90%-100% range instead of 100%-110% range
        index = 9;
    }

    // Do linear interpolation (weighted average)
    return linear_map(
        // Comments show what happens when we want to move meter to 72%.
        10*index,  // 70
        10*(index + 1),  // 80
        cconf->calibration[index],  // volume at 70%
        cconf->calibration[index + 1],  // volume at 80%
        percentage  // 72
    );
}

static void prepare_audio_data(const struct Config *conf, int16_t *dest, int samples_per_channel)
{
    float gains[2] = { get_gain(&conf->channels[0]), get_gain(&conf->channels[1]) };
    double pi = acos(-1);

    for (int i = 0; i < samples_per_channel; i++) {
        for (int ch = 0; ch < 2; ch++) {
            float gain = gains[ch];
            double time = i / (double)conf->sample_rate;

            double sample = gain * sin(2 * pi * conf->frequency * time);
            assert(-1 <= sample && sample <= 1);
            *dest++ = (int16_t)(0x7fff * sample);
        }
    }
}


struct Process {
    pid_t pid;
    int stdin_fd;
};

static struct Process start_aplay(const struct Config *conf)
{
    char sample_rate[100];
    sprintf(sample_rate, "%d", conf->sample_rate);

    char buffer_time_usec[100];
    sprintf(buffer_time_usec, "%d", (int)(conf->refresh_interval * 1000 * 1000));

    const char *const args[] = {
        "aplay",
        "--format", "S16_LE",
        "--rate", sample_rate,
        "--channels", "2",
        "--device", conf->audio_device,
        "--buffer-time", buffer_time_usec,
        NULL,
    };

    int stdin_pipe[2];
    if (pipe(stdin_pipe) != 0) {
        fail("pipe() failed");
    }

    posix_spawn_file_actions_t actions;
    posix_spawn_file_actions_init(&actions);
    // Subpricess sets read end of pipe as the stdin
    posix_spawn_file_actions_adddup2(&actions, stdin_pipe[0], STDIN_FILENO);
    // Then it closes both ends of the pipe (does not close the duplication)
    posix_spawn_file_actions_addclose(&actions, stdin_pipe[0]);
    posix_spawn_file_actions_addclose(&actions, stdin_pipe[1]);

    pid_t pid;
    int ret = posix_spawnp(&pid, "aplay", &actions, NULL, (char *const*)args, NULL);
    if (ret != 0) {
        fail("starting aplay failed: %s", strerror(errno));
    }

    // Parent process only need write to pipe, close read end
    close(stdin_pipe[0]);

    return (struct Process){ .pid = pid, .stdin_fd = stdin_pipe[1] };
}


static struct timespec get_current_time(void)
{
    struct timespec result;
    int ret = clock_gettime(CLOCK_MONOTONIC, &result);
    if (ret != 0) {
        fail("clock_gettime() failed: %s", strerror(errno));
    }
    return result;
}

static const long one_sec_as_nanosec = 1000L * 1000L * 1000L;

static struct timespec add_timespecs(const struct timespec *a, const struct timespec *b)
{
    time_t sec = a->tv_sec + b->tv_sec;
    long long nanosec = (long long)a->tv_nsec + (long long)b->tv_nsec;
    if (nanosec > one_sec_as_nanosec) {
        nanosec -= one_sec_as_nanosec;
        sec++;
    }

    assert(0 <= nanosec && nanosec < one_sec_as_nanosec);
    return (struct timespec){ .tv_sec=sec, .tv_nsec=nanosec };
}

static struct timespec subtract_timespecs(const struct timespec *a, const struct timespec *b)
{
    time_t sec = a->tv_sec - b->tv_sec;
    long nanosec = a->tv_nsec - b->tv_nsec;

    if (nanosec > one_sec_as_nanosec) {
        nanosec -= one_sec_as_nanosec;
        sec++;
    }
    if (nanosec < 0) {
        nanosec += one_sec_as_nanosec;
        sec--;
    }

    assert(0 <= nanosec && nanosec < one_sec_as_nanosec);
    return (struct timespec){ .tv_sec=sec, .tv_nsec=nanosec };
}

static struct timespec negate_timespec(const struct timespec *t)
{
    return subtract_timespecs(&(struct timespec){0}, t);
}

static bool timespec_is_negative(const struct timespec *t)
{
    assert(0 <= t->tv_nsec && t->tv_nsec < one_sec_as_nanosec);
    return t->tv_sec < 0;
}

static struct timespec float_seconds_to_timespec(float seconds)
{
    int sec = (int)seconds;
    long nanosec = (long)((seconds - sec) * one_sec_as_nanosec);
    return (struct timespec){ .tv_sec = sec, .tv_nsec = nanosec };
}

static void wait_given_interval(struct timespec *t, float interval)
{
    struct timespec ispec = float_seconds_to_timespec(interval);
    *t = add_timespecs(t, &ispec);

    struct timespec now = get_current_time();
    struct timespec wait_time = subtract_timespecs(t, &now);
    if (timespec_is_negative(&wait_time)) {
        // we are lagging behind, skip waiting
        *t = now;
        struct timespec lag = negate_timespec(&wait_time);
        show_warning("lagged %d.%09ld seconds", (int)lag.tv_sec, (long)lag.tv_nsec);
    } else {
        nanosleep(&wait_time, NULL);
    }
}


static int write_all(int fd, const void *buf, size_t nbytes)
{
    while (nbytes > 0) {
        ssize_t wrote = write(fd, buf, nbytes);
        if (wrote <= 0) {
            return -1;
        }
        nbytes -= wrote;
    }
    return 0;
}


int main(int argc, char **argv)
{
    if (argc != 2 || argv[1][0] == '-') {
        // TODO: test this
        fprintf(stderr, "Usage: %s your-mittari-config-file.conf\n", argv[0]);
        return 2;
    }

    // Ignore SIGPIPE signal, so I can handle aplay problems myself.
    // This process gets SIGPIPE when aplay dies.
    signal(SIGPIPE, SIG_IGN);

    struct Config conf;
    read_config_file(argv[1], &conf);

    int samples_per_channel = (int)(conf.sample_rate * conf.refresh_interval);
    int16_t *audio_data = malloc(2 * samples_per_channel * sizeof(audio_data[0]));

    struct Process aplay = start_aplay(&conf);
    struct timespec wait_state = get_current_time();

    while(true) {
        prepare_audio_data(&conf, audio_data, samples_per_channel);
        if (write_all(aplay.stdin_fd, audio_data, 2 * samples_per_channel * sizeof(audio_data[0])) != 0) {
            show_warning("there seems to be a problem with aplay, restarting in 1 second");

            kill(aplay.pid, SIGKILL);
            waitpid(aplay.pid, NULL, 0);

            nanosleep(&(struct timespec){ .tv_sec = 1 }, NULL);
            aplay = start_aplay(&conf);
        }
        wait_given_interval(&wait_state, conf.refresh_interval);
    }
}
