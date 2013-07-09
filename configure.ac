#                                               -*- Autoconf -*-
# Process this file with autoconf to produce a configure script.

AC_PREREQ([2.69])
AC_INIT([melodia], [0.1], [echooatmeal@gmail.com])
AC_CONFIG_SRCDIR([src/player.c])
AC_CONFIG_HEADER([config.h])
# TODO: standardize
AM_INIT_AUTOMAKE([foreign])

# Checks for programs.
AC_PROG_CC
AC_PROG_LN_S
AC_PATH_PROG([PYTHON], [python2], AC_MSG_ERROR([python 2.x not found]))

# Checks for libraries.
SDL_VERSION=1.2.0
AM_PATH_SDL($SDL_VERSION, :, AC_MSG_ERROR([SDL version $SDL_VERSION not found]))
CFLAGS="$CFLAGS $SDL_CFLAGS"
LIBS="$LIBS $SDL_LIBS"
AC_CHECK_LIB([avcodec], [avcodec_decode_audio4], , AC_MSG_ERROR([libavcodec not found]))
AC_CHECK_LIB([avformat], [avformat_open_input], , AC_MSG_ERROR([libavformat not found]))
AC_CHECK_LIB([avutil], [av_malloc], , AC_MSG_ERROR([libavutil not found]))
AC_CHECK_LIB([swresample], [swr_convert], , AC_MSG_ERROR([libswresample not found]))

# Checks for header files.
AC_CHECK_HEADERS([sys/socket.h unistd.h], , AC_MSG_ERROR([headers for socket functions not found]))
AC_CHECK_HEADERS([libavcodec/avcodec.h libavformat/avformat.h libswresample/swresample.h], , AC_MSG_ERROR([libav* headers not found]))

# Checks for typedefs, structures, and compiler characteristics.
AC_TYPE_INT64_T
AC_TYPE_SIZE_T
AC_TYPE_SSIZE_T
AC_TYPE_UINT8_T

# Checks for library functions.
AC_FUNC_FORK
AC_FUNC_MALLOC
AC_CHECK_FUNCS([memset select socket], , AC_MSG_ERROR([necessary functions not found]))

AC_OUTPUT(Makefile src/Makefile)
