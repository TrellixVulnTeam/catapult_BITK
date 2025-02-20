# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import six

from dashboard.api import api_request_handler
from dashboard.pinpoint.models import change
from dashboard.common import utils

if utils.IsRunningFlask():
  from flask import request

  def _CheckUser():
    pass

  @api_request_handler.RequestHandlerDecoratorFactory(_CheckUser)
  def CommitHandlerPost():
    repository = request.args.get('repository', 'chromium')
    git_hash = request.args.get('git_hash')
    try:
      c = change.Commit.FromDict({
          'repository': repository,
          'git_hash': git_hash,
      })
      return c.AsDict()
    except KeyError as e:
      six.raise_from(
          api_request_handler.BadRequestError('Unknown git hash: %s' %
                                              git_hash), e)
else:
  # pylint: disable=abstract-method
  class Commit(api_request_handler.ApiRequestHandler):

    def _CheckUser(self):
      pass

    def Post(self, *args, **kwargs):
      del args, kwargs  # Unused.
      repository = self.request.get('repository', 'chromium')
      git_hash = self.request.get('git_hash')
      try:
        c = change.Commit.FromDict({
            'repository': repository,
            'git_hash': git_hash,
        })
        return c.AsDict()
      except KeyError as e:
        six.raise_from(
            api_request_handler.BadRequestError('Unknown git hash: %s' %
                                                git_hash), e)
