#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libswresample/swresample.h>

#include "SDL.h"
#include "SDL_thread.h"

#include <stdio.h>
#include <time.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <signal.h>
#include <sys/wait.h>

#define SDL_AUDIO_BUFFER_SIZE 1024

typedef struct PacketQueue {
	AVPacketList *first_pkt, *last_pkt;
	int nb_packets;
	int size;
	int quit;
	SDL_mutex *mutex;
	SDL_cond *cond;
} PacketQueue;

typedef struct AudioParams {
	int freq;
	int channels;
	int64_t channel_layout;
	enum AVSampleFormat fmt;
} AudioParams;

typedef struct File {
	FILE *fp;
	long long filesize, pos;
} File;

typedef struct State {
	int audioStream;
	PacketQueue audioq;
	AVCodecContext *codec_ctx;
	AVFormatContext *format_ctx;
	AudioParams audio_src, audio_tgt;
	AVStream *audio_st;
	AVPacket audio_pkt, audio_pkt1;
	AVFrame audio_frame1;
	struct SwrContext *swr_ctx;
	uint8_t audio_buf[(AVCODEC_MAX_AUDIO_FRAME_SIZE * 3) / 2];
	unsigned int audio_buf_size;
	unsigned int audio_buf_index;
	uint8_t *audio_buf1;
	unsigned int audio_buf1_size;
	double audio_clock;
	double audio_clock_drift;
	File *file;
	int paused;
	int quit;
	int buffering;
} State;

const char *socket_addr = "/tmp/melodia-socket";

void sigterm_handler(int sig) {
	unlink(socket_addr);
	exit(0);
}

void sigchld_handler(int sig) {
	int stat;
	while (waitpid(-1, &stat, WNOHANG) > 0);
}

void packet_queue_init(PacketQueue *q) {
	memset(q, 0, sizeof(PacketQueue));
	q->mutex = SDL_CreateMutex();
	q->cond = SDL_CreateCond();
}
int packet_queue_put(PacketQueue *q, AVPacket *pkt) {

	AVPacketList *pkt1;
	if (av_dup_packet(pkt) < 0)
		return -1;
	pkt1 = av_malloc(sizeof(AVPacketList));
	if (! pkt1)
		return -1;
	pkt1->pkt = *pkt;
	pkt1->next = NULL;

	SDL_LockMutex(q->mutex);

	if (! q->last_pkt)
		q->first_pkt = pkt1;
	else
		q->last_pkt->next = pkt1;
	q->last_pkt = pkt1;
	q->nb_packets++;
	q->size += pkt1->pkt.size;
	SDL_CondSignal(q->cond);

	SDL_UnlockMutex(q->mutex);
	return 0;
}
int packet_queue_get(PacketQueue *q, AVPacket *pkt, int block) {
	AVPacketList *pkt1;
	int ret;

	SDL_LockMutex(q->mutex);

	for (;;) {
		if (q->quit) {
			ret = -1;
			break;
		}

		pkt1 = q->first_pkt;
		if (pkt1) {
			q->first_pkt = pkt1->next;
			if (! q->first_pkt)
				q->last_pkt = NULL;
			q->nb_packets--;
			q->size -= pkt1->pkt.size;
			*pkt = pkt1->pkt;
			av_free(pkt1);
			ret = 1;
			break;
		} else if (! block) {
			ret = 0;
			break;
		} else
			SDL_CondWait(q->cond, q->mutex);
	}
	SDL_UnlockMutex(q->mutex);
	return ret;
}

int audio_decode_frame(State *is) {

	int64_t dec_channel_layout;
	int len1, len2, data_size = 0;

	for (;;) {
		if (is->paused)
			return -1;

		while (is->audio_pkt1.size > 0) {

			int got_frame = 0;
			len1 = avcodec_decode_audio4(is->codec_ctx, &is->audio_frame1, &got_frame, &is->audio_pkt1);
			if (len1 < 0) {
				/* if error, skip frame */
				is->audio_pkt1.size = 0;
				break;
			}
			is->audio_pkt1.data += len1;
			is->audio_pkt1.size -= len1;
			if (got_frame) {
				dec_channel_layout =
					(is->audio_frame1.channel_layout && av_frame_get_channels(&is->audio_frame1) == av_get_channel_layout_nb_channels(is->audio_frame1.channel_layout)) ?
					is->audio_frame1.channel_layout : av_get_default_channel_layout(av_frame_get_channels(&is->audio_frame1));
				data_size = av_samples_get_buffer_size(NULL, av_frame_get_channels(&is->audio_frame1), is->audio_frame1.nb_samples, is->audio_frame1.format, 1);

				if (is->audio_frame1.format != is->audio_src.fmt || dec_channel_layout != is->audio_src.channel_layout || is->audio_frame1.sample_rate != is->audio_src.freq) {
					if (is->swr_ctx) swr_free(&is->swr_ctx);
					is->swr_ctx = swr_alloc_set_opts(NULL, is->audio_tgt.channel_layout, is->audio_tgt.fmt, is->audio_tgt.freq, dec_channel_layout,
							is->audio_frame1.format, is->audio_frame1.sample_rate, 0, NULL);
					if (! is->swr_ctx || swr_init(is->swr_ctx) < 0) {
						fprintf(stderr, "Cannot create sample rate converter\n");
						break;
					}
					is->audio_src.channel_layout = dec_channel_layout;
					is->audio_src.channels = av_frame_get_channels(&is->audio_frame1);
					is->audio_src.freq = is->audio_frame1.sample_rate;
					is->audio_src.fmt = is->audio_frame1.format;
				}

				if (is->swr_ctx) {
					const uint8_t **in = (const uint8_t **)is->audio_frame1.extended_data;
					uint8_t **out = &is->audio_buf1;
					int out_count = (int64_t)is->audio_frame1.nb_samples * is->audio_tgt.freq / is->audio_frame1.sample_rate + 256;
					int out_size = av_samples_get_buffer_size(NULL, is->audio_tgt.channels, out_count, is->audio_tgt.fmt, 0);

					av_fast_malloc(&is->audio_buf1, &is->audio_buf1_size, out_size);
					len2 = swr_convert(is->swr_ctx, out, out_count, in, is->audio_frame1.nb_samples);
					if (len2 < 0) {
						fprintf(stderr, "swr_convert() failed\n");
						break;
					}
					data_size = len2 * is->audio_tgt.channels * av_get_bytes_per_sample(is->audio_tgt.fmt);
					memcpy(is->audio_buf, is->audio_buf1, data_size);
				} else
					memcpy(is->audio_buf, is->audio_frame1.data[0], data_size);
				is->audio_clock += (double)data_size / (av_frame_get_channels(&is->audio_frame1) * is->audio_frame1.sample_rate * av_get_bytes_per_sample(is->audio_frame1.format));
			}

			/* We have data, return it and come back for more later */
			return data_size;
		}

		if (is->audio_pkt.data)
			av_free_packet(&is->audio_pkt);

		if (is->quit)
			return -1;

		if (packet_queue_get(&is->audioq, &is->audio_pkt, 1) < 0)
			return -1;
		is->audio_pkt1 = is->audio_pkt;

		if (is->audio_pkt.pts != AV_NOPTS_VALUE)
			is->audio_clock = av_q2d(is->audio_st->time_base) * is->audio_pkt.pts;
	}
}

void audio_callback(void *userdata, Uint8 *stream, int len) {

	State *is = (State *)userdata;
	int len1, audio_size;
	double now = av_gettime() / 1000000.0;

	while (len > 0) {
		if (is->audio_buf_index >= is->audio_buf_size) {
			/* We have already sent all our data; get more */
			audio_size = audio_decode_frame(is);
			if (audio_size < 0) {
				/* If error, output silence */
				is->audio_buf_size = 1024; // arbitrary?
				memset(is->audio_buf, 0, is->audio_buf_size);
			} else
				is->audio_buf_size = audio_size;
			is->audio_buf_index = 0;
		}
		len1 = is->audio_buf_size - is->audio_buf_index;
		if(len1 > len)
			len1 = len;
		memcpy(stream, (uint8_t *)is->audio_buf + is->audio_buf_index, len1);
		len -= len1;
		stream += len1;
		is->audio_buf_index += len1;
	}

	is->audio_clock_drift = is->audio_clock - now;
}

int readfunc(void *ptr, uint8_t *buf, int bufsize) {
	File *file = ptr;
	size_t num = fread(buf, 1, bufsize, file->fp);
	file->pos += num;
	return num;
}

int64_t seekfunc(void *ptr, int64_t pos, int whence) {
	File *file = ptr;
	if (whence == AVSEEK_SIZE) return file->filesize;
	else return -1;
}

int read_thread(void *arg) {
	AVPacket packet;
	State *is = arg;
	int ret;

	// Read frames
	while (1) {
		if (is->quit) break;

		if (is->audioq.nb_packets > 5) {
			av_usleep(0.01 * 1000000);
			continue;
		}

		ret = av_read_frame(is->format_ctx, &packet);
		if (ret < 0) {
			if (is->file->pos == is->file->filesize)
				break;
			else {
				av_usleep(0.01 * 1000000);
				continue;
			}
		}

		if (packet.stream_index == is->audioStream)
			packet_queue_put(&is->audioq, &packet);
		else
			av_free_packet(&packet);
		// Free the packet that was allocated by av_read_frame
	}

	return 0;
}

int handle(int fd) {
	State *is;
	AVProbeData probeData;
	AVIOContext* io_ctx;
	AVCodec *codec = NULL;
	SDL_Thread *read_tid;
	SDL_AudioSpec wanted_spec, spec;
	AVDictionaryEntry *item = NULL;

	const int bufsize = 32 * 1024;
	unsigned char *buf;
	char socket_buf[100], *pos;
	fd_set readfds;
	struct timeval timeout;
	int i;
	ssize_t nbytes;

	is = (State *)malloc(sizeof(State));
	buf = malloc(bufsize);

	// Register all formats and codecs
	av_register_all();

	if (SDL_Init(SDL_INIT_AUDIO | SDL_INIT_TIMER)) {
		fprintf(stderr, "Could not initialize SDL - %s\n", SDL_GetError());
		exit(1);
	}

	if ((nbytes = read(fd, socket_buf, 100)) < 0)
		return -1;
	socket_buf[nbytes] = 0;
	is->file = malloc(sizeof(File));
	is->file->fp = fopen(socket_buf, "r");
	if (is->file->fp == NULL)
		return -1;

	sprintf(socket_buf, "SIZE");
	write(fd, socket_buf, strlen(socket_buf));

	if ((nbytes = read(fd, socket_buf, 100)) < 0)
		return -1;
	socket_buf[nbytes] = 0;
	sscanf(socket_buf, "%lld", &is->file->filesize);
	is->file->pos = 0;

	io_ctx = avio_alloc_context(buf, bufsize, 0, is->file, readfunc, NULL, seekfunc);
	is->format_ctx = avformat_alloc_context();

	probeData.buf = buf;
	probeData.buf_size = bufsize;
	probeData.filename = "";

	is->format_ctx->pb = io_ctx;
	is->format_ctx->iformat = av_probe_input_format(&probeData, 1);
	is->format_ctx->flags = AVFMT_FLAG_CUSTOM_IO;

	// Open video file
	if (avformat_open_input(&is->format_ctx, "", NULL, NULL) != 0)
		return -1; // Couldn't open file

	// Retrieve stream information
	if (avformat_find_stream_info(is->format_ctx, NULL) < 0)
		return -1; // Couldn't find stream information

	// Find the first video stream
	is->audioStream=-1;
	for (i = 0; i < is->format_ctx->nb_streams; i++)
		if (is->format_ctx->streams[i]->codec->codec_type == AVMEDIA_TYPE_AUDIO && is->audioStream < 0)
			is->audioStream = i;
	if (is->audioStream == -1)
		return -1;

	is->audio_st = is->format_ctx->streams[is->audioStream];
	is->codec_ctx = is->format_ctx->streams[is->audioStream]->codec;
	// Set audio settings from codec info
	wanted_spec.freq = is->codec_ctx->sample_rate;
	wanted_spec.format = AUDIO_S16SYS;
	wanted_spec.channels = av_get_channel_layout_nb_channels(is->codec_ctx->channel_layout);
	wanted_spec.silence = 0;
	wanted_spec.samples = SDL_AUDIO_BUFFER_SIZE;
	wanted_spec.callback = audio_callback;
	wanted_spec.userdata = is;

	if (SDL_OpenAudio(&wanted_spec, &spec) < 0) {
		fprintf(stderr, "SDL_OpenAudio: %s\n", SDL_GetError());
		return -1;
	}

	is->audio_src.fmt = AV_SAMPLE_FMT_S16;
	is->audio_src.freq = spec.freq;
	is->audio_src.channel_layout = is->codec_ctx->channel_layout;
	is->audio_src.channels = spec.channels;
	if (! is->audio_src.channel_layout || is->audio_src.channels != av_get_channel_layout_nb_channels(is->audio_src.channel_layout)) {
		is->audio_src.channel_layout = av_get_default_channel_layout(is->audio_src.channels);
		is->audio_src.channel_layout &= ~AV_CH_LAYOUT_STEREO_DOWNMIX;
	}
	is->audio_tgt = is->audio_src;

	codec = avcodec_find_decoder(is->codec_ctx->codec_id);
	if (! codec) {
		fprintf(stderr, "Unsupported codec!\n");
		return -1;
	}
	int ret = avcodec_open2(is->codec_ctx, codec, NULL);

	packet_queue_init(&is->audioq);
	SDL_PauseAudio(0);
	is->audio_clock = 0;
	is->audio_clock_drift = -av_gettime() / 1000000.0;

	if (! (read_tid = SDL_CreateThread(read_thread, is))) {
		fprintf(stderr, "Cannot create thread!\n");
		return -1;
	}

	pos = socket_buf;
	pos += sprintf(pos, "%d", (int) (is->format_ctx->duration / 1000000));
	while (item = av_dict_get(is->format_ctx->metadata, "", item, AV_DICT_IGNORE_SUFFIX))
		if (strcmp(item->key, "artist") == 0 || strcmp(item->key, "album") == 0 || strcmp(item->key, "title") == 0)
			pos += sprintf(pos, "\1%s\2%s", item->key, item->value);
	write(fd, socket_buf, pos - socket_buf);

	if (read(fd, socket_buf, 100) < 0)
		return -1;

	int seconds = 0;
	av_usleep(0.01 * 1000000);
	while (! is->quit) {

		if (! is->buffering && is->audioq.size == 0 && is->file->pos < is->file->filesize) {
			is->buffering = 1;
			strcpy(socket_buf, "BUFFERING");
			write(fd, socket_buf, strlen(socket_buf) + 1);
		}
		if (is->audioq.size > 0 && is->buffering) {
			is->buffering = 0;
			strcpy(socket_buf, "RESUME");
			write(fd, socket_buf, strlen(socket_buf) + 1);
		}

		if (! is->paused && ! is->buffering) {
			double cur_clock = is->audio_clock_drift + av_gettime() / 1000000.0;
			if (cur_clock * 1000000 >= is->format_ctx->duration) break;
			if ((int) cur_clock > seconds) {
				seconds = cur_clock;
				sprintf(socket_buf, "%d", seconds);
				write(fd, socket_buf, strlen(socket_buf) + 1);
			}
		}

		FD_ZERO(&readfds);
		FD_SET(fd, &readfds);
		timeout.tv_sec = 0;
		timeout.tv_usec = 0.01 * 1000000;
		if (select(fd + 1, &readfds, NULL, NULL, &timeout) > 0) {
			if ((nbytes = read(fd, socket_buf, 100)) <= 0)
				is->quit = 1;
			else {
				socket_buf[nbytes] = 0;
				if (strcmp(socket_buf, "PAUSE") == 0) is->paused = 1;
				else if (strcmp(socket_buf, "RESUME") == 0) is->paused = 0;
				else if (strcmp(socket_buf, "QUIT") == 0) is->quit = 1;
			}
		}
	}

	strcpy(socket_buf, "QUIT");
	write(fd, socket_buf, strlen(socket_buf) + 1);

	is->quit = 1;
	is->audioq.quit = 1;
	SDL_CondSignal(is->audioq.cond);
	SDL_WaitThread(read_tid, NULL);

	AVPacketList *pkt, *pkt1;
	for (pkt = is->audioq.first_pkt; pkt != NULL; pkt = pkt1) {
		pkt1 = pkt->next;
		av_free_packet(&pkt->pkt);
		av_freep(&pkt);
	}
	SDL_DestroyMutex(is->audioq.mutex);
	SDL_DestroyCond(is->audioq.cond);
	SDL_Quit();

	// Close the video file
	fclose(is->file->fp);
	free(is->file);
	avformat_close_input(&is->format_ctx);
	swr_free(&is->swr_ctx);
	if (is->audio_buf1) av_free(is->audio_buf1);
	av_free(io_ctx);
	free(is);

	close(fd);

	return 0;
}

int main() {
	struct sockaddr_un addr;
	addr.sun_family = AF_UNIX;
	strcpy(addr.sun_path, socket_addr);

	int fd = socket(AF_UNIX, SOCK_STREAM, 0);
	if (fd < 0)
		return -1;
	if (bind(fd, (struct sockaddr *) &addr, sizeof(addr)) < 0)
		return -1;
	if (listen(fd, 5) < 0)
		return -1;

	signal(SIGINT, sigterm_handler);
	signal(SIGTERM, sigterm_handler);
	signal(SIGCHLD, sigchld_handler);

	int client;

	while ((client = accept(fd, NULL, NULL)) >= 0)
		if (fork() == 0) {
			handle(client);
			return 0;
		}

	return 0;
}
