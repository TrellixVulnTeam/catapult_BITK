# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import json
import re
import unittest

import mock
import webapp2
import webtest

from dashboard import buildbucket_job_status
from dashboard.common import testing_common
from dashboard.common import utils
from dashboard.services import request

SAMPLE_RESPONSE = r"""{
 "build": {
  "status": "COMPLETED",
  "created_ts": "1430771172999340",
  "url": "http://build.chromium.org/p/tryserver.chromium.perf/builders\
/linux_perf_bisector/builds/32",
  "bucket": "master.tryserver.chromium.perf",
  "result_details_json": "{\"properties\": {\
\"got_nacl_revision\": \"660eb1e1c91349b53f0d60bbf9a92e31f4cf4e1d\", \
\"got_swarming_client_revision\": \
\"f222001cc23c7cdb574bf4cfb447f65c94bc6da3\", \
\"got_revision\": \"d558f46c34085abfc9f59824fdc3466f45c40152\", \
\"build_url\": \"gs://chrome-perf/Linux Bisector\", \
\"recipe\": \"bisect\", \
\"got_webrtc_revision_cp\": \"refs/heads/master@{#9128}\", \
\"got_webkit_revision_git\": \"44bf01091874592828070dc26cbb5189da9b959b\", \
\"append_deps_patch_sha\": true, \
\"project\": \"\", \
\"got_webkit_revision\": 194864, \
\"slavename\": \"build74-m4\", \
\"got_revision_cp\": \"refs/heads/master@{#328178}\", \
\"blamelist\": [], \
\"branch\": \"\", \
\"revision\": \"\", \
\"workdir\": \"/b/build/slave/linux_perf_bisector\", \
\"repository\": \"\", \
\"buildername\": \"linux_perf_bisector\", \
\"got_webrtc_revision\": \"0d778c6af22767e9bcc92a278da08b5f82885977\", \
\"mastername\": \"tryserver.chromium.perf\", \
\"got_v8_revision\": \"a06f1b4e013812cc7ad1d52a0ea49206cafa7b67\", \
\"got_v8_revision_cp\": \"refs/heads/4.4.50@{#1}\", \
\"buildbotURL\": \"http://build.chromium.org/p/tryserver.chromium.perf/\", \
\"bisect_config\": {\"good_revision\": \"328111\", \
\"builder_host\": null, \
\"metric\": \"record_time/record_time\", \
\"max_time_minutes\": \"20\", \
\"builder_port\": null, \
\"bug_id\": null, \
\"command\": \"src/tools/perf/run_benchmark -v --browser=release \
rasterize_and_record_micro.key_mobile_sites_smooth\", \
\"repeat_count\": \"20\", \
\"test_type\": \"perf\", \
\"gs_bucket\": \"chrome-perf\", \
\"bad_revision\": \"328115\"}, \
\"got_webkit_revision_cp\": \"refs/heads/master@{#194864}\", \
\"buildnumber\": 32, \
\"requestedAt\": 1430771180}}",
  "status_changed_ts": "1430771433288620",
  "created_by": "user:425761728072-pa1bs18esuhp2cp2qfa1u9vb6p1v6kfu\
@developer.gserviceaccount.com",
  "failure_reason": "BUILD_FAILURE",
  "result": "FAILURE",
  "utcnow_ts": "1430863009872910",
  "id": "9046721402459257808",
  "parameters_json": "{\"builder_name\": \"linux_perf_bisector\", \
\"properties\": {\"bisect_config\": {\"bad_revision\": \"328115\", \
\"bug_id\": null, \
\"builder_host\": null, \
\"builder_port\": null, \
\"command\": \"src/tools/perf/run_benchmark -v --browser=release \
rasterize_and_record_micro.key_mobile_sites_smooth\", \
\"good_revision\": \"328111\", \
\"gs_bucket\": \"chrome-perf\", \
\"max_time_minutes\": \"20\", \
\"metric\": \"record_time/record_time\", \
\"repeat_count\": \"20\", \
\"test_type\": \"perf\"}}}",
  "completed_ts": "1430771433288680",
  "updated_ts": "1430771433288850"
 },
 "kind": "buildbucket#resourcesItem",
 "etag": "\"mWAxLWqIHM8gXvavjiTVUApk92U/AaU08KGmhFQcdRWOCVgNYJBBlgI\""
}""".replace('\\\n', '')

SAMPLE_RESPONSE_NOT_FOUND = r"""{
 "error": {
  "message": "",
  "reason": "BUILD_NOT_FOUND"
 },
 "kind": "buildbucket#resourcesItem",
 "etag": "\"mWAxLWqIHM8gXvavjiTVUApk92U/vcsTyxWNZoEnszG8qWqlQLOhpl8\""
}"""


class BuildbucketJobStatusTest(testing_common.TestCase):

  def setUp(self):
    super(BuildbucketJobStatusTest, self).setUp()
    app = webapp2.WSGIApplication([
        (r'/buildbucket_job_status/(\d+)',
         buildbucket_job_status.BuildbucketJobStatusHandler)
    ])
    self.testapp = webtest.TestApp(app)

  @mock.patch.object(buildbucket_job_status.buildbucket_service, 'GetJobStatus',
                     mock.MagicMock(return_value=json.loads(SAMPLE_RESPONSE)))
  @mock.patch.object(utils, 'IsRunningBuildBucketV2', lambda: False)
  def testGet_ExistingJob(self):
    response = self.testapp.get('/buildbucket_job_status/9046721402459257808')
    # Verify that a human-readable creation time is presented. We check for the
    # minute:second string to avoid localization from breaking this test.
    self.assertIn('26:12', response.body)
    # Verify that both the good and bad revisions are displayed somewhere.
    self.assertIn('328115', response.body)
    self.assertIn('328111', response.body)
    # Verify that a link to buildbot is provided somewhere.
    self.assertTrue(
        re.search('href\\s*=\\s*[\'"]http://build.chromium.org/p/tryserver',
                  response.body, re.IGNORECASE))

  @mock.patch.object(
      buildbucket_job_status.buildbucket_service, 'GetJobStatus',
      mock.MagicMock(return_value=json.loads(SAMPLE_RESPONSE_NOT_FOUND)))
  @mock.patch.object(utils, 'IsRunningBuildBucketV2', lambda: False)
  def testGet_JobNotFound(self):
    response = self.testapp.get('/buildbucket_job_status/9046721402459257808')
    # If the error code is shown somewhere in the page and no exception is
    # raised, that's good enough.
    self.assertIn('BUILD_NOT_FOUND', response)

  @mock.patch.object(
      buildbucket_job_status.buildbucket_service, 'GetJobStatus',
      mock.MagicMock(return_value=json.loads(r"""{"status": "SUCCESS"}""")))
  @mock.patch.object(buildbucket_job_status.BuildbucketJobStatusHandler,
                     'RenderHtml')
  @mock.patch.object(utils, 'IsRunningBuildBucketV2', lambda: True)
  def testGet_ExistingJobV2(self, render):
    self.testapp.get('/buildbucket_job_status/12345')
    render.assert_called_once_with(
        'buildbucket_job_status.html', {
            'job_id': '12345',
            'status_text': 'DATA:{\n    "status": "SUCCESS"\n}',
            'build': {
                "status": "SUCCESS"
            },
            'error': None,
            'original_response': {
                "status": "SUCCESS"
            }
        })

  @mock.patch.object(buildbucket_job_status.buildbucket_service, 'GetJobStatus',
                     mock.MagicMock(
                         side_effect=request.NotFoundError(
                             'oops', {'x-prpc-grpc-code': '5'}, 'Error msg.')))
  @mock.patch.object(buildbucket_job_status.BuildbucketJobStatusHandler,
                     'RenderHtml')
  @mock.patch.object(utils, 'IsRunningBuildBucketV2', lambda: True)
  def testGet_JobNotFoundV2(self, render):
    self.testapp.get('/buildbucket_job_status/12345')
    render.assert_called_once_with(
        'buildbucket_job_status.html', {
            'job_id': '12345',
            'status_text': 'DATA:Error msg.',
            'build': None,
            'error': 'gRPC code: 5',
            'original_response': 'Error msg.'
        })


if __name__ == '__main__':
  unittest.main()
