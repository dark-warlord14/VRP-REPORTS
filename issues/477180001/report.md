# Service Worker subresource responses expose detailed resource timing information for cross-origin resources that are normally restricted, leading to an information leak in the Resource Timing API

| Field | Value |
|-------|-------|
| **Issue ID** | [477180001](https://issues.chromium.org/issues/477180001) |
| **Status** | Accepted |
| **Severity** | S3-Low |
| **Priority** | P2 |
| **Component** | Blink>PerformanceAPIs>ResourceTiming |
| **Platforms** | Android, Linux, Mac, Windows, ChromeOS |
| **Reporter** | po...@gmail.com |
| **Assignee** | su...@google.com |
| **Created** | 2026-01-20 |
| **Bounty** | $2,000.00 |

## Description

---

### Report description

Service Worker subresource responses expose detailed resource timing information for cross-origin resources that are normally restricted, leading to an information leak in the Resource Timing API

---

### Bug location

#### Where do you want to report your vulnerability?

Chrome VRP – Report security issues affecting the Chrome browser. [See program rules](https://bughunters.google.com/about/rules/5745167867576320/chrome-vulnerability-reward-program-rules)

#### Which URL (or repository) have you found the vulnerability in?

<https://chromium.googlesource.com/chromium/src/>

---

### The problem

#### Please describe the technical details of the vulnerability

Chromium exposes detailed network timing and size information for resources via the Resource Timing API (`performance.getEntriesByType("resource")`). To protect cross-origin privacy, these details are only supposed to be available when the response satisfies the Timing-Allow-Origin (TAO) policy or is same-origin with the calling context.

For subresources intercepted by a Service Worker, the renderer-side subresource loader assumes that constructed responses are always same-origin with the client and unconditionally marks them as passing the timing allow check, regardless of the actual response origin or TAO headers.

In `ServiceWorkerSubresourceLoader::StartResponse` the URL loader head is filled from the Service Worker `FetchAPIResponse`, and then `timing_allow_passed` is set to `true` for all constructed subresource responses:

```
// chromium/src/content/renderer/service_worker/service_worker_subresource_loader.cc
void ServiceWorkerSubresourceLoader::StartResponse(
    blink::mojom::FetchAPIResponsePtr response,
    blink::mojom::ServiceWorkerStreamHandlePtr body_as_stream) {
  // ...
  blink::ServiceWorkerLoaderHelpers::SaveResponseInfo(*response,
                                                      response_head_.get());
  response_head_->response_start = base::TimeTicks::Now();
  response_head_->load_timing.receive_headers_start = base::TimeTicks::Now();
  response_head_->load_timing.receive_headers_end =
      response_head_->load_timing.receive_headers_start;
  response_source_ = response->response_source;

  // Constructed subresource responses are always same-origin as the requesting
  // client.
  response_head_->timing_allow_passed = true;
  // ...
}

```

By contrast, the normal network loader path computes `timing_allow_passed` based on an explicit timing-allow-origin check:

```
// chromium/src/services/network/cors/cors_url_loader.cc
// (simplified)
timing_allow_failed_flag_ = !PassesTimingAllowOriginCheck(*response_head);
response_head->timing_allow_passed = !timing_allow_failed_flag_;

```

On the Blink side, this `timing_allow_passed` flag directly controls whether detailed timing and connection metadata are exposed to JavaScript. In `CreateResourceTimingInfo`, if `TimingAllowPassed()` is true, the `allow_timing_details` flag is set and the full set of fields are populated:

```
// chromium/src/third_party/blink/renderer/platform/loader/fetch/resource_timing_utils.cc
mojom::blink::ResourceTimingInfoPtr CreateResourceTimingInfo(
    base::TimeTicks start_time,
    const KURL& initial_url,
    const ResourceResponse* response) {
  mojom::blink::ResourceTimingInfoPtr info =
      mojom::blink::ResourceTimingInfo::New();
  info->start_time = start_time;
  info->name = initial_url;
  info->response_end = base::TimeTicks::Now();
  if (!response) {
    return info;
  }

  if (response->TimingAllowPassed()) {
    info->allow_timing_details = true;
    info->server_timing = ParseServerTimingFromHeaderValueToMojo(
        response->HttpHeaderField(http_names::kServerTiming));
    info->cache_state = response->CacheState();
    info->alpn_negotiated_protocol = response->AlpnNegotiatedProtocol().IsNull()
                                         ? g_empty_string
                                         : response->AlpnNegotiatedProtocol();
    info->connection_info = response->ConnectionInfoString().IsNull()
                                ? g_empty_string
                                : response->ConnectionInfoString();

    info->did_reuse_connection = response->ConnectionReused();
    // Use SecurityOrigin::Create to handle cases like blob:https://.
    info->is_secure_transport = base::Contains(
        url::GetSecureSchemes(),
        SecurityOrigin::Create(response->ResponseUrl())->Protocol().Ascii());
    info->timing = response->GetResourceLoadTiming()
                       ? response->GetResourceLoadTiming()->ToMojo()
                       : nullptr;
  } else {
    // Only limited timing fields are exposed when the timing allow check fails.
    // ...
  }
  // ...
}

```

`ResourceResponse` explicitly documents that the response URL may differ from the request URL when a Service Worker responds with a different underlying resource:

```
// chromium/src/third_party/blink/renderer/platform/loader/fetch/resource_response.h
// ...
// Specifically, if a service worker responded to the request for this
// resource, it may have fetched an entirely different URL and responded with
// that resource. WasFetchedViaServiceWorker() and ResponseUrl() can be used
// to determine whether and how a service worker responded to the request.
// Example service worker code:
//
// onfetch = (event => {
//   if (event.request.url == 'https://abc.com')
//     event.respondWith(fetch('https://def.com'));
// });
//
// If this service worker responds to an "https://abc.com" request, then for
// the resulting ResourceResponse, CurrentRequestUrl() is "https://abc.com",
// WasFetchedViaServiceWorker() is true, and ResponseUrl() is
// "https://def.com".
const KURL& CurrentRequestUrl() const;
void SetCurrentRequestUrl(const KURL&);
// ...
KURL ResponseUrl() const;

```

The test code under `web/fetch_timing/` sets up exactly this pattern:

- An HTML page served from one origin, for example `http://localhost:8080/index.html`, registers a Service Worker whose scope covers `/proxy`.
- The page offers two actions:
  - Load a resource directly from `http://localhost:9000/target.bin` via an `<img>` tag (cross-origin request).
  - Load the same underlying resource via a same-origin `<img src="/proxy?...">`, where the Service Worker fetches `http://localhost:9000/target.bin` with `mode: "no-cors"` and returns the response.
- After each load, the page inspects `performance.getEntriesByType("resource")` and logs key fields (`responseStart`, `responseEnd`, `transferSize`, `encodedBodySize`, `decodedBodySize`, `nextHopProtocol`) for the corresponding `PerformanceResourceTiming` entry.

In this setup:

- The direct cross-origin load from `http://localhost:8080` to `http://localhost:9000/target.bin` produces a timing entry where sensitive fields are cleared or zeroed, for example:
  
  - `responseStart: 0`
  - `transferSize: 0`
  - `encodedBodySize: 0`
  - `decodedBodySize: 0`
  - `nextHopProtocol: ""`
- The Service Worker–mediated load uses a same-origin URL such as `http://localhost:8080/proxy?...` as the observable resource name, but the Service Worker internally fetches the cross-origin target from `http://localhost:9000`. For this entry, the logged timing data includes detailed values, for example:
  
  - non-zero `responseStart` and `responseEnd`
  - `transferSize` and `nextHopProtocol` populated

This demonstrates that code running in the origin that controls the Service Worker can obtain detailed timing and size information about a resource whose actual origin is different and that does not opt in via `Timing-Allow-Origin`.

#### Impact analysis

Who can exploit the vulnerability:

- Any web origin that can register and control a Service Worker for its own pages can exploit this issue for subresource requests it initiates (for example, an attacker-controlled site with a Service Worker whose scope covers a `/proxy` path).

What they gain when doing so:

- The attacking origin can obtain detailed timing and connection metadata (such as non-zero `responseStart` / `responseEnd`, `transferSize`, `encodedBodySize`, `decodedBodySize`, and `nextHopProtocol`) for resources that are actually fetched from a different origin and would normally have these fields restricted by the Resource Timing API.
- This additional information can be used to:
  - perform cross-site performance and availability probing of arbitrary URLs reachable from the browser;
  - infer limited aspects of user or server state from response timing and size patterns (for example, presence of particular resources or cache behavior);
  - strengthen cross-origin device or network fingerprinting by incorporating timing and protocol characteristics of external resources.

---

### The cause

#### What version of Chrome have you found the security issue in?

145.0.7632.1/stable

#### Is the security issue related to a crash?

No, it is not related to a crash.

#### Choose the type of vulnerability

Information Leak

#### How would you like to be publicly acknowledged for your report?

Povcfe of Tencent Security Xuanwu Lab

## Attachments

- fetch_timing.mp4 (video/mp4, 2.0 MB)
- [fetch_timing.zip](attachments/fetch_timing.zip) (application/x-zip-compressed, 4.9 KB)

## Timeline

### po...@gmail.com (2026-01-20)

## patch

```
diff --git a/chromium/src/content/renderer/service_worker/service_worker_subresource_loader.cc b/chromium/src/content/renderer/service_worker/service_worker_subresource_loader.cc
--- a/chromium/src/content/renderer/service_worker/service_worker_subresource_loader.cc
+++ b/chromium/src/content/renderer/service_worker/service_worker_subresource_loader.cc
@@ -20,9 +20,11 @@
 #include "base/trace_event/trace_event.h"
 #include "content/common/features.h"
 #include "content/common/fetch/fetch_request_type_converters.h"
 #include "content/common/service_worker/race_network_request_url_loader_client.h"
 #include "content/common/service_worker/service_worker_router_evaluator.h"
 #include "content/public/common/content_features.h"
 #include "content/renderer/service_worker/controller_service_worker_connector.h"
 #include "mojo/public/cpp/bindings/self_owned_receiver.h"
 #include "net/base/net_errors.h"
 #include "net/url_request/redirect_util.h"
 #include "net/url_request/url_request.h"
 #include "services/network/public/cpp/features.h"
+#include "services/network/public/cpp/timing_allow_origin_parser.h"
 #include "services/network/public/cpp/record_ontransfersizeupdate_utils.h"
 #include "services/network/public/cpp/resource_request.h"
 #include "services/network/public/cpp/shared_url_loader_factory.h"
 #include "services/network/public/mojom/early_hints.mojom.h"
 #include "services/network/public/mojom/service_worker_router_info.mojom.h"
 #include "services/network/public/mojom/url_response_head.mojom.h"
 #include "third_party/blink/public/common/blob/blob_utils.h"
 #include "third_party/blink/public/common/service_worker/service_worker_loader_helpers.h"
 #include "third_party/blink/public/common/service_worker/service_worker_type_converters.h"
 #include "third_party/blink/public/mojom/blob/blob.mojom.h"
 #include "third_party/blink/public/mojom/service_worker/dispatch_fetch_event_params.mojom.h"
 #include "third_party/blink/public/mojom/service_worker/service_worker_fetch_handler_bypass_option.mojom-shared.h"
 #include "third_party/blink/public/mojom/service_worker/service_worker_stream_handle.mojom.h"
 #include "third_party/blink/public/platform/web_url_response.h"
 #include "third_party/perfetto/include/perfetto/tracing/track.h"
+#include "url/origin.h"
 
 namespace content {
 
 namespace {
@@ -899,11 +901,38 @@ void ServiceWorkerSubresourceLoader::StartResponse(
   response_head_->load_timing.receive_headers_start = base::TimeTicks::Now();
   response_head_->load_timing.receive_headers_end =
       response_head_->load_timing.receive_headers_start;
   response_source_ = response->response_source;
 
-  // Constructed subresource responses are always same-origin as the requesting
-  // client.
-  response_head_->timing_allow_passed = true;
+  // Compute the timing allow result for the constructed subresource response.
+  // Service workers may respond with a resource from a different origin, so
+  // base the decision on the request initiator, the effective response URL
+  // and any Timing-Allow-Origin header when available.
+  response_head_->timing_allow_passed = true;
+  if (resource_request_.request_initiator) {
+    const url::Origin& initiator = *resource_request_.request_initiator;
+
+    // Determine the effective response origin. When a service worker responds
+    // with a resource fetched from a different URL, the last entry in
+    // url_list_via_service_worker is the underlying response URL; otherwise
+    // fall back to the request URL.
+    url::Origin response_origin;
+    if (!response_head_->url_list_via_service_worker.empty()) {
+      response_origin = url::Origin::Create(
+          response_head_->url_list_via_service_worker.back());
+    } else {
+      response_origin = url::Origin::Create(resource_request_.url);
+    }
+
+    bool allow = false;
+    if (initiator.IsSameOriginWith(response_origin)) {
+      allow = true;
+    } else if (response_head_->parsed_headers &&
+               response_head_->parsed_headers->timing_allow_origin) {
+      allow = network::TimingAllowOriginCheck(
+          response_head_->parsed_headers->timing_allow_origin, initiator);
+    }
+
+    response_head_->timing_allow_passed = allow;
+  }
 
   // Set the actual source type to `kFetchEvent` if nothing is set yet.
   auto* router_info = response_head_->service_worker_router_info.get();
   if (router_info && router_info->matched_source_type &&
       !router_info->actual_source_type) {


```

### el...@chromium.org (2026-01-22)

Security shepherd: thanks for the report!

I am not quite sure how to reproduce this locally, but it looks plausible enough that I'm going to pass it directly to the Blink performance APIs team for further triage. Under our security guidelines I think this is at worst a cross-resource info leak (and not a particularly powerful one) so I'm going to call this Sev-2 and mark it as affecting all platforms where Blink & our net stack is used.

### el...@chromium.org (2026-01-22)

Assigning to yoavweiss out of //third\_party/blink/renderer/core/timing/OWNERS :)

### dc...@chromium.org (2026-01-22)

Safari seems to behave this way as well, but not Firefox. I'm not sure exactly what the spec here says, but it would make sense to not reveal the timing information here.

### mm...@google.com (2026-01-22)

CC @su...@google.com and @yy...@google.com, who I think have done recent work to SW+RT.

### yo...@chromium.org (2026-01-23)

Skimming through the Fetch spec, the [TAO check](https://fetch.spec.whatwg.org/#ref-for-concept-tao-check) happens below SW interception, so should apply.

### ch...@google.com (2026-01-23)

Setting milestone because of s2 severity.

### yo...@chromium.org (2026-01-23)

Reassigning to suzukikeita@ as the SW RT experts.

### nr...@chromium.org (2026-01-23)

Note that the timing info passed to the document, by spec, is separate from the one passed to the service worker. So it shouldn't include any information about the cross-origin resource.
Specifically for the rest:

- responseStart measures timing related to the service worker itself, unrelated to the underlying resource, so they are safe. See <https://wpt.fyi/results/service-workers/service-worker/resource-timing-fetch-variants.https.html?label=experimental>
- decodedBodySize/encodedBodySize depend on CORS and not on TAO.
- nextHopProtocol should indeed not be exposed,

The tests above assert a lot of this, but I see that they don't include nextHopProtocol, so that might need to be addressed, and going over all of the attributes is not a bad idea.

### yy...@google.com (2026-01-26)

Thanks for the insights, Noam. I agree that a more granular masking logic—allowing SW-related stats like responseStart while hiding network-specific details—would be the ideal approach.

However, implementing this properly would likely require a new state or attribute to represent SW-proxied cross-origin subresources, which might involve specification alignment in addition to the code changes. Given the P2/S2 nature of this issue and our current high-priority commitments, we unfortunately don't have the bandwidth to dedicate to such complex work immediately.

Unless we want to land the reporter's simpler patch now, which I assume might be overly restrictive as it would mask even the safe SW-related timings, we'd like to move this to our backlog for a proper fix later. Does that sound reasonable?

### nr...@chromium.org (2026-01-26)

There is no need for spec alignment. The spec already covers it... what needs to be done is to follow the spec and have the information to not bleed through when forwarding the response from the service worker to the client. The proposed patch here would regress metrics and would replace one bug with another.

### dx...@google.com (2026-02-02)

Project: chromium/src  

Branch:  main  

Author:  Noam Rosenthal [nrosenthal@chromium.org](mailto:nrosenthal@chromium.org)  

Link:    <https://chromium-review.googlesource.com/7516608>

Clear connection timing when service-worker response is passed to resource timing.

---


Expand for full commit details
```
     
    By spec, this information is part of the fetch rather than the response, 
    and the connection info for a response passed from a service worker is 
    not the connection info of the client's fetch. 
     
    Bug: 477180001 
    Change-Id: I98145f0976eb8d301a21c20e3c7892a96edd9274 
    Reviewed-on: https://chromium-review.googlesource.com/c/chromium/src/+/7516608 
    Commit-Queue: Noam Rosenthal <nrosenthal@google.com> 
    Reviewed-by: Yoav Weiss (@Shopify) <yoavweiss@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#1578031}

```

---

Files:

- M `third_party/blink/renderer/platform/loader/fetch/resource_timing_utils.cc`
- M `third_party/blink/web_tests/external/wpt/service-workers/service-worker/next-hop-protocol.https.html`
- M `third_party/blink/web_tests/external/wpt/service-workers/service-worker/resource-timing-cross-origin.https.html`

---

Hash: [88392b548909e77969f21eeab3249d87e8164509](https://chromiumdash.appspot.com/commit/88392b548909e77969f21eeab3249d87e8164509)  

Date: Mon Feb 2 11:48:35 2026


---

### ch...@google.com (2026-02-02)

Security Merge Request Consideration: Requesting merge to beta (M145) because latest trunk commit (1578031) appears to be after beta branch point (1568190).
Security Merge Request: Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).

We have determined this fix is necessary on milestone(s): [].

Please answer the following questions so that we can safely process this merge request:

1. Which CLs should be backmerged? (Please include Gerrit links.)
2. Has this fix been verified on Canary to not pose any stability regressions?
3. Does this fix pose any potential non-verifiable stability risks?
4. Does this fix pose any known compatibility risks?
5. Does it require manual verification by the test team? If so, please describe required testing.
6. (no answer required) Please check the OS custom field to ensure all impacted OSes are checked!

### ch...@google.com (2026-02-03)

Merge review required: M145 has already been cut for stable release.

Please answer the following questions so that we can safely process your merge request:

1. Why does your merge fit within the merge criteria for these milestones?

- Chrome Browser: <https://chromiumdash.appspot.com/branches>
- Chrome OS: <https://goto.google.com/cros-release-branch-merge-guidelines>

2. What changes specifically would you like to merge? Please link to Gerrit.
3. Have the changes been released and tested on canary?
4. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?
5. [Chrome OS only]: Was the change reviewed and approved by the Eng Prod Representative? <https://goto.google.com/cros-engprodcomponents>
6. If this merge addresses a major issue in the stable channel, does it require manual verification by the test team? If so, please describe required testing.

Please contact the milestone owner if you have questions.
Owners: andywu (ChromeOS), srinivassista (Desktop US), None (Desktop EMEA), harrysouders (Mobile US), eakpobaro (Mobile EMEA)

### nr...@chromium.org (2026-02-03)

This is an old same-origin-policy leak. I don't see an urgency with backporting it to existing releases.

### dr...@chromium.org (2026-02-03)

Agreed, thanks. Updating labels.

### sp...@google.com (2026-02-20)

** NOTE: This is an automatically generated email **

Hello,

Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $2000.00 for this report.

Rationale for this decision:
Low impact user information disclosure


Important: This payment will be issued by Bugcrowd. You will receive an email from Bugcrowd in the next 24 hours which contains a submission you must claim to be rewarded.

If you do not receive an email from them, please check your spam folder and then reach out to us via a comment here. For issues related to Bugcrowd itself, please contact them via https://bugcrowd.com/support.


Thank you for your efforts and helping us make Chrome more secure for all users!

Cheers,
Chrome VRP Panel Bot


P.S. One other thing we'd like to mention:

* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.

Please contact security-vrp@chromium.org with any questions.

### ch...@google.com (2026-05-12)

This bug has been closed for more than 14 weeks. Removing issue access restrictions.

## Bounty Award

> Low impact user information disclosure

---
*Data from [Chromium Issue Tracker](https://issues.chromium.org/issues/477180001)*
