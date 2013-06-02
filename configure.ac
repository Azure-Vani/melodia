#                                               -*- Autoconf -*-
# Process this file with autoconf to produce a configure script.

AC_PREREQ([2.69])
AC_INIT([melodia], [0.1], [echooatmeal@gmail.com])
AC_CONFIG_SRCDIR([src/player.c])
# TODO: standardize
AM_INIT_AUTOMAKE([foreign])

# Checks for programs.
AC_PROG_CC

# Checks for libraries.
SDL_VERSION=1.2.0
AM_PATH_SDL($SDL_VERSION, :, AC_MSG_ERROR([SDL version $SDL_VERSION not found!]))
CFLAGS="$CFLAGS $SDL_FLAGS"
LIBS="$LIBS $SDL_LIBS"
AC_CHECK_LIB([avcodec], [avcodec_decode_audio4])
AC_CHECK_LIB([avformat], [avformat_open_input])
AC_CHECK_LIB([avutil], [av_malloc])
AC_CHECK_LIB([swresample], [swr_convert])

# Checks for header files.
AC_CHECK_HEADERS([sys/socket.h unistd.h])
AC_CHECK_HEADERS([libavcodec/avcodec.h libavformat/avformat.h libswresample/swresample.h])

# Checks for typedefs, structures, and compiler characteristics.
AC_TYPE_INT64_T
AC_TYPE_SIZE_T
AC_TYPE_SSIZE_T
AC_TYPE_UINT8_T

# Checks for library functions.
AC_FUNC_FORK
AC_FUNC_MALLOC
AC_CHECK_FUNCS([memset select socket])

AC_OUTPUT(Makefile src/Makefile)
