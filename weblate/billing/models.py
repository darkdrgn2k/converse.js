# -*- coding: utf-8 -*-
#
# Copyright © 2012 - 2015 Michal Čihař <michal@cihar.com>
#
# This file is part of Weblate <https://weblate.org/>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import unicode_literals
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from datetime import timedelta

from weblate.trans.models import Project, SubProject, Change
from weblate.lang.models import Language


class Plan(models.Model):
    name = models.CharField(max_length=100, unique=True)
    price = models.IntegerField(default=0)
    yearly_price = models.IntegerField(default=0)
    limit_strings = models.IntegerField(default=0)
    display_limit_strings = models.IntegerField(default=0)
    limit_languages = models.IntegerField(default=0)
    display_limit_languages = models.IntegerField(default=0)
    limit_repositories = models.IntegerField(default=0)
    display_limit_repositories = models.IntegerField(default=0)
    limit_projects = models.IntegerField(default=0)
    display_limit_projects = models.IntegerField(default=0)

    class Meta(object):
        ordering = ['price']

    def __unicode__(self):
        return self.name


class Billing(models.Model):
    plan = models.ForeignKey(Plan)
    user = models.OneToOneField(User)
    projects = models.ManyToManyField(Project, blank=True)
    trial = models.BooleanField(default=False)

    def __unicode__(self):
        return '{0} ({1})'.format(self.user, self.plan)

    def count_changes(self, interval):
        return Change.objects.filter(
            subproject__project__in=self.projects.all(),
            timestamp__gt=timezone.now() - interval,
        ).count()

    def count_changes_1m(self):
        return self.count_changes(timedelta(days=31))
    count_changes_1m.short_description = _('Changes in last month')

    def count_changes_1q(self):
        return self.count_changes(timedelta(days=93))
    count_changes_1q.short_description = _('Changes in last quarter')

    def count_changes_1y(self):
        return self.count_changes(timedelta(days=365))
    count_changes_1y.short_description = _('Changes in last year')

    def count_repositories(self):
        return SubProject.objects.filter(
            project__in=self.projects.all(),
        ).exclude(
            repo__startswith='weblate:/'
        ).count()
    count_repositories.short_description = _('VCS repositories')

    def count_strings(self):
        return sum(
            [p.get_total() for p in self.projects.all()]
        )
    count_strings.short_description = _('Source strings')

    def count_words(self):
        return sum(
            [p.get_total_words() for p in self.projects.all()]
        )
    count_words.short_description = _('Source words')

    def count_languages(self):
        return Language.objects.filter(
            translation__subproject__project__in=self.projects.all()
        ).distinct().count()
    count_languages.short_description = _('Languages')

    def in_limits(self):
        return (
            (
                self.plan.limit_repositories == 0 or
                self.count_repositories() <= self.plan.limit_repositories
            ) and
            (
                self.plan.limit_projects == 0 or
                self.projects.count() <= self.plan.limit_projects
            ) and
            (
                self.plan.limit_strings == 0 or
                self.count_strings() <= self.plan.limit_strings
            ) and
            (
                self.plan.limit_languages == 0 or
                self.count_languages() <= self.plan.limit_languages
            )
        )
    in_limits.boolean = True
