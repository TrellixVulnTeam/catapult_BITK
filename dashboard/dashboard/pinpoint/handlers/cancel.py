# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import json

from dashboard.api import api_request_handler
from dashboard.api import api_auth
from dashboard.common import utils
from dashboard.pinpoint.models import job as job_module
from dashboard.pinpoint.models import errors

if utils.IsRunningFlask():
  from flask import request, make_response

  def _CheckUser():
    if utils.IsDevAppserver():
      return
    api_auth.Authorize()
    if not utils.IsTryjobUser():
      raise api_request_handler.ForbiddenError()

  @api_request_handler.RequestHandlerDecoratorFactory(_CheckUser)
  def CancelHandlerPost():
    args = utils.RequestParamsMixed(request)
    job_id = args.get('job_id')
    reason = args.get('reason')

    if not job_id or not reason:
      raise api_request_handler.BadRequestError()

    job = job_module.JobFromId(job_id)
    if not job:
      raise api_request_handler.NotFoundError()

    # Enforce first that only the users that started the job and administrators
    # can cancel jobs.
    requester_email = utils.GetEmail()
    delegated_email = args.get('user')

    # Here, we check that the requester email is in a list of service accounts
    # that we support delegation for.
    if delegated_email and utils.IsAllowedToDelegate(requester_email):
      email = delegated_email
    else:
      email = requester_email
    if not utils.IsAdministrator(email) and email != job.user:
      raise api_request_handler.ForbiddenError()

    # Truncate the reason down to 255 caracters including ellipses.
    try:
      job.Cancel(email, reason[:252] + '...' if len(reason) > 255 else reason)
      return {'job_id': job.job_id, 'state': 'Cancelled'}
    except errors.CancelError as e:
      return make_response(
          json.dumps({
              'job_id': job.job_id,
              'message': str(e)
          }), 400)

else:
  # pylint: disable=abstract-method
  class Cancel(api_request_handler.ApiRequestHandler):

    required_arguments = {'job_id', 'reason'}

    def _CheckUser(self):
      self._CheckIsLoggedIn()
      if not utils.IsTryjobUser():
        raise api_request_handler.ForbiddenError()

    def Post(self, *args, **kwargs):
      del args, kwargs  # Unused.
      # Pull out the Job ID and reason in the request.
      args = self.request.params.mixed()
      job_id = args.get('job_id')
      reason = args.get('reason')
      if not job_id or not reason:
        raise api_request_handler.BadRequestError()

      job = job_module.JobFromId(job_id)
      if not job:
        raise api_request_handler.NotFoundError()

      # Enforce first that only the users that started the job and
      # administrators can cancel jobs.
      requester_email = utils.GetEmail()
      delegated_email = args.get('user')

      # Here, we check that the requester email is in a list of service accounts
      # that we support delegation for.
      if delegated_email and utils.IsAllowedToDelegate(requester_email):
        email = delegated_email
      else:
        email = requester_email
      if not utils.IsAdministrator(email) and email != job.user:
        raise api_request_handler.ForbiddenError()

      # Truncate the reason down to 255 caracters including ellipses.
      try:
        job.Cancel(email, reason[:252] + '...' if len(reason) > 255 else reason)
        return {'job_id': job.job_id, 'state': 'Cancelled'}
      except errors.CancelError as e:
        self.response.set_status(400)
        return {'job_id': job.job_id, 'message': str(e)}
