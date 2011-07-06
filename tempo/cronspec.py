# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2009-2011, Ask Solem and contributors.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
# Neither the name of Ask Solem nor the names of its contributors may be used
# to endorse or promote products derived from this software without specific
# prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from pyparsing import (Word, Literal, ZeroOrMore, Optional,
                       Group, StringEnd, alphas)


DAYNAMES = "sun", "mon", "tue", "wed", "thu", "fri", "sat"
WEEKDAYS = dict((name, dow) for name, dow in zip(DAYNAMES, range(7)))


class cronexpr_parser(object):
    """Parser for crontab expressions. Any expression of the form 'groups'
    (see BNF grammar below) is accepted and expanded to a set of numbers.
    These numbers represent the units of time that the crontab needs to
    run on::

        digit   :: '0'..'9'
        dow     :: 'a'..'z'
        number  :: digit+ | dow+
        steps   :: number
        range   :: number ( '-' number ) ?
        numspec :: '*' | range
        expr    :: numspec ( '/' steps ) ?
        groups  :: expr ( ',' expr ) *

    The parser is a general purpose one, useful for parsing hours, minutes and
    day_of_week expressions.  Example usage::

        >>> minutes = cronexpr_parser(60).parse("*/15")
        [0, 15, 30, 45]
        >>> hours = cronexp_parser(24).parse("*/4")
        [0, 4, 8, 12, 16, 20]
        >>> day_of_week = cronexpr_parser(7).parse("*")
        [0, 1, 2, 3, 4, 5, 6]

    """

    def __init__(self, max_=60):
        # define the grammar structure
        digits = "0123456789"
        star = Literal('*')
        number = Word(digits) | Word(alphas)
        steps = number
        range_ = number + Optional(Literal('-') + number)
        numspec = star | range_
        expr = Group(numspec) + Optional(Literal('/') + steps)
        extra_groups = ZeroOrMore(Literal(',') + expr)
        groups = expr + extra_groups + StringEnd()

        # define parse actions
        star.setParseAction(self._expand_star)
        number.setParseAction(self._expand_number)
        range_.setParseAction(self._expand_range)
        expr.setParseAction(self._filter_steps)
        extra_groups.setParseAction(self._ignore_comma)
        groups.setParseAction(self._join_to_set)

        self.max_ = max_
        self.parser = groups

    @staticmethod
    def _expand_number(toks):
        try:
            i = int(toks[0])
        except ValueError:
            try:
                return WEEKDAYS[toks[0][0:3].lower()]
            except KeyError:
                raise ValueError("Invalid weekday literal '%s'." % toks[0])
        return [i]

    @staticmethod
    def _expand_range(toks):
        if len(toks) > 1:
            return range(toks[0], int(toks[2]) + 1)
        else:
            return toks[0]

    def _expand_star(self, toks):
        return range(self.max_)

    @staticmethod
    def _filter_steps(toks):
        numbers = toks[0]
        if len(toks) > 1:
            steps = toks[2]
            return [n for n in numbers if n % steps == 0]
        else:
            return numbers

    @staticmethod
    def _ignore_comma(toks):
        return [x for x in toks if x != ',']

    @staticmethod
    def _join_to_set(toks):
        return set(toks.asList())

    def parse(self, cronexpr):
        return self.parser.parseString(cronexpr).pop()


class cronspec(object):
    """Like a :manpage:`cron` job, you can specify units of time of when
    you would like the task to execute. It is a reasonably complete
    implementation of cron's features, so it should provide a fair
    degree of scheduling needs.

    You can specify a minute, an hour, and/or a day of the week in any
    of the following formats:

    .. attribute:: minute

        - A (list of) integers from 0-59 that represent the minutes of
          an hour of when execution should occur; or
        - A string representing a crontab expression.  This may get pretty
          advanced, like `minute="*/15"` (for every quarter) or
          `minute="1,13,30-45,50-59/2"`.

    .. attribute:: hour

        - A (list of) integers from 0-23 that represent the hours of
          a day of when execution should occur; or
        - A string representing a crontab expression.  This may get pretty
          advanced, like `hour="*/3"` (for every three hours) or
          `hour="0,8-17/2"` (at midnight, and every two hours during
          office hours).

    .. attribute:: day_of_week

        - A (list of) integers from 0-6, where Sunday = 0 and Saturday =
          6, that represent the days of a week that execution should
          occur.
        - A string representing a crontab expression.  This may get pretty
          advanced, like `day_of_week="mon-fri"` (for weekdays only).
          (Beware that `day_of_week="*/2"` does not literally mean
          "every two days", but "every day that is divisible by two"!)

    """

    @staticmethod
    def _expand_cronexpr(cronexpr, max_, dow_wrap=False):
        """Takes the given cronexpr argument in one of the forms::

            int         (like 7)
            basestring  (like '3-5,*/15', '*', or 'monday')
            set         (like set([0,15,30,45]))
            list        (like [8-17])

        And convert it to an (expanded) set representing all time unit
        values on which the crontab triggers.  Only in case of the base
        type being 'basestring', parsing occurs.  (It is fast and
        happens only once for each cronspec instance, so there is no
        significant performance overhead involved.)

        For the other base types, merely Python type conversions happen.

        The argument `max_` is needed to determine the expansion of '*'.

        """
        def is_iterable(obj):
            try:
                iter(obj)
            except TypeError:
                return False
            return True

        if isinstance(cronexpr, int):
            result = set([cronexpr])
        elif isinstance(cronexpr, basestring):
            result = cronexpr_parser(max_).parse(cronexpr)
        elif isinstance(cronexpr, set):
            result = cronexpr
        elif is_iterable(cronexpr):
            result = set(cronexpr)
        else:
            raise TypeError(
                    "Argument cronexpr needs to be of any of the "
                    "following types: int, basestring, or an iterable type. "
                    "'%s' was given." % type(cronexpr))

        if dow_wrap:
            result = set([0 if n == max_ else n for n in result])

        # assure the result does not exceed the max
        for number in result:
            if number >= max_:
                raise ValueError(
                        "Invalid crontab expression. Valid "
                        "range is 0-%d. '%d' was found." % (max_ - 1, number))

        return result

    def __init__(self, minute='*', hour='*', day_of_week='*'):
        self._orig_minute = minute
        self._orig_hour = hour
        self._orig_day_of_week = day_of_week
        self.hour = self._expand_cronexpr(hour, 24)
        self.minute = self._expand_cronexpr(minute, 60)
        self.day_of_week = self._expand_cronexpr(day_of_week, 7, dow_wrap=True)

    def __repr__(self):
        return "<cronspec: %s %s %s (m/h/d)>" % (self._orig_minute or "*",
                                                self._orig_hour or "*",
                                                self._orig_day_of_week or "*")

    def __str__(self):
        return "%s %s %s" % (self._orig_minute or "*",
                             self._orig_hour or "*",
                             self._orig_day_of_week or "*")

def parse(spec):
    return cronspec(*spec.split(' '))
