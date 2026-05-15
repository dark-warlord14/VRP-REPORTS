# Leaking size of cross-origin resources via rangeless opaque responses using Service Workers and the Fetch API

| Field | Value |
|-------|-------|
| **Issue ID** | [474435504](https://issues.chromium.org/issues/474435504) |
| **Status** | Assigned |
| **Severity** | S3-Low |
| **Priority** | P1 |
| **Component** | Blink>Network>FetchAPI |
| **Platforms** | Android, Linux, Mac, Windows, ChromeOS |
| **Reporter** | he...@gmail.com |
| **Assignee** | yy...@chromium.org |
| **Created** | 2026-01-09 |
| **Bounty** | $3,000.00 |

## Description

#### VULNERABILITY DETAILS

When a cross-origin resource is used in an audio/video tag, a request containing the Range header asking for `bytes=0-` is issued. If the request is intercepted using a Service Worker and we respond with an arbitrary Content-Range header, e.g:

```
e.respondWith(new Response("A".repeat(size), {status: 206, headers: { "Content-Range": "bytes 0-5000/13337" }}));

```

Chrome will be tricked into thinking it got the first `size` bytes of the audio/video and then ask for the remaining bytes by issuing a new request containing the `Range: bytes=${size}-` header.

If we also intercept the following request and send it again using the Fetch API, the request will be sent to the cross-origin server containing the Range header and there will be two possible outcomes:

1. The server will return a `416 Range Not Satisfiable` response status code if the cross-origin response size is smaller than `size` bytes.
2. The server will return a `206 Partial Content` response status code if the cross-origin response size is bigger than `size` bytes.

We can then store this response and use the service worker to return it when a different resource is fetched (e.g., `/mock.css` with `mode: "no-cors"`).

In the case of fetch requests, if the stored response contains a 206 status code, it will fail because Chrome has a security check in `resource_loader.cc:950-958` that blocks opaque responses with status 206 when `has_range_requested` is true but the original request didn't have a Range header.

However, if the stored response contains a 416 status code, this check is skipped because it only triggers for status code 206, not 416, causing the fetch to succeed normally.

This difference in behavior (206 throws an error, 416 succeeds) can be observed using a try/catch block, thus creating an oracle that allows an attacker to detect the possible outcomes mentioned above and leak the exact size of cross-origin resources that accept range requests.

The root cause is in `third_party/blink/renderer/platform/loader/fetch/resource_loader.cc:950-958`:

```
// A response should not serve partial content if it was not requested via a
// Range header: https://fetch.spec.whatwg.org/#main-fetch
if (response.GetType() == network::mojom::FetchResponseType::kOpaque &&
    response.HttpStatusCode() == 206 && response.HasRangeRequested() &&
    !initial_request.HttpHeaderFields().Contains(http_names::kRange)) {
  HandleError(ResourceError::CancelledDueToAccessCheckError(
      response.CurrentRequestUrl(), ResourceRequestBlockedReason::kOther));
  return;
}

```

The check only blocks responses with status code 206, but does not block 416 responses, allowing the information leak.

In the PoC, the size of <https://www.google.com/robots.txt> is being brute-forced through a binary search attack.

This vulnerability is useful for XS-Search attacks. A real-world example is <https://medium.com/@luanherrera/xs-searching-googles-bug-tracker-to-find-out-vulnerable-source-code-50d8135b7549> (more on <https://github.com/xsleaks/xsleaks/wiki/Real-World-Examples>).

For more context, this is a variation of <https://crbug.com/chromium/990849> (which I reported a few years ago). I have also attached a video reproducing the attack (`repro.mp4`).

#### BISECT

By doing an initial bisect, I found that the issue was introduce between 800651 and 800665 (<https://chromium.googlesource.com/chromium/src/+log/d474076dff70b3df138c423225c74cb011e750b7..676c68c320a484dc95ed5060d81af7b71d55153b>).

After investigating, it became clear that the commit that introduced the issue is <https://chromium.googlesource.com/chromium/src/+/5da0ed1e65305ab2c6d9de2bb4ce62f159520ba8>, and it landed on M87.0.4241.0.

#### VERSION

Chrome Version: 143.0.7499.170 (Stable)   

Chrome Version: 144.0.7559.31 (Beta)   

Chrome Version: 145.0.7587.5 (Dev)   

Chrome Version: 145.0.7618.0 (Canary)   

Operating System: Windows 11 24H2

#### REPRODUCTION CASE

1. Download the following files: `index.html` and `sw.js`.
2. Move all files into the same folder.
3. Serve the files using a web server (e.g., `python -m http.server 8080`).
4. Navigate to <http://localhost:8080/index.html>.
5. The page will automatically register the service worker.
6. Enter a URL in the input field (default is <https://www.google.com/robots.txt>) and click the `Run` button.
7. The exact response size of the cross-origin resource will be leaked via a binary search attack, with results displayed on the page.

#### CREDIT INFORMATION

Reporter credit: Luan Herrera (@lbherrera\_)

## Attachments

- [index.html](attachments/index.html) (text/html, 3.1 KB)
- [sw.js](attachments/sw.js) (text/javascript, 755 B)
- [repro.mp4](attachments/repro.mp4) (video/mp4, 5.3 MB)

## Timeline

### ct...@chromium.org (2026-01-13)

Thank you for the very clear report!

Adding blink/loader OWNERs and assigning to toyoshim@. Please reroute as needed if you think someone else can help.

Setting some security labels as well: Sev-High (S1) for what seems like a fairly robust XS-leak, FoundIn-142 for current extended stable (but thank you for the very far back bisect as well). Conservatively setting all Blink platforms as well.

### ch...@google.com (2026-01-13)

Setting milestone because of s0/s1 severity.

### ch...@google.com (2026-01-13)

Setting Priority to P1 to match Severity s1. If this is incorrect, please reset the priority. The automation bot account won't make this change again.

### to...@chromium.org (2026-01-13)

Let me route this to Yanagisawa as this is related to SW.
Also CC Networking API team members, and some members who are working on SW.

### yy...@chromium.org (2026-01-14)

Thanks for heads up.  I suppose this is not only a Chromium issue but also the specification issue.
I have filed https://github.com/whatwg/fetch/issues/1906
I suppose https://github.com/whatwg/fetch/commit/4e322096f225c4c65a29e2b82419fb66516e480c is needed for this.

### dx...@google.com (2026-01-15)

Project: chromium/src  

Branch:  main  

Author:  Yoshisato Yanagisawa [yyanagisawa@chromium.org](mailto:yyanagisawa@chromium.org)  

Link:    <https://chromium-review.googlesource.com/7453440>

Block opaque 416 responses to non-range requests

---


Expand for full commit details
```
     
    Extend the security check for opaque 206 responses to also cover 
    416 responses when the request does not contain a Range header. This 
    makes the handling of these responses symmetric. 
     
    This change is controlled by the 'kBlockPartialResponseWithoutRange' 
    feature flag. 
     
    See: https://github.com/whatwg/fetch/issues/1906 
     
    Bug: 474435504 
    Change-Id: Ifbc4b9b9ea9f45ef6b5a0d3705de5368a1ee0227 
    Reviewed-on: https://chromium-review.googlesource.com/c/chromium/src/+/7453440 
    Reviewed-by: Takashi Toyoshima <toyoshim@chromium.org> 
    Commit-Queue: Yoshisato Yanagisawa <yyanagisawa@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#1569484}

```

---

Files:

- M `third_party/blink/common/features.cc`
- M `third_party/blink/public/common/features.h`
- M `third_party/blink/renderer/platform/loader/fetch/resource_loader.cc`
- M `third_party/blink/renderer/platform/loader/fetch/resource_loader_test.cc`

---

Hash: [c0e8cebca540579fa734bbca6ffc1e280982857f](https://chromiumdash.appspot.com/commit/c0e8cebca540579fa734bbca6ffc1e280982857f)  

Date: Thu Jan 15 03:28:36 2026


---

### yy...@chromium.org (2026-01-15)

I confirmed that the CL (#comment7) neutralized the attack code explained in #comment1.

### ch...@google.com (2026-01-15)

Security Merge Request Consideration: Requesting merge to stable (M144) because latest trunk commit (1569484) appears to be after stable branch point (1552494).
Security Merge Request Consideration: Requesting merge to beta (M145) because latest trunk commit (1569484) appears to be after beta branch point (1568190).
Security Merge Request: Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).

We have determined this fix is necessary on milestone(s): [].

Please answer the following questions so that we can safely process this merge request:

1. Which CLs should be backmerged? (Please include Gerrit links.)
2. Has this fix been verified on Canary to not pose any stability regressions?
3. Does this fix pose any potential non-verifiable stability risks?
4. Does this fix pose any known compatibility risks?
5. Does it require manual verification by the test team? If so, please describe required testing.
6. (no answer required) Please check the OS custom field to ensure all impacted OSes are checked!

### yy...@chromium.org (2026-01-15)

1. Which CLs should be backmerged? (Please include Gerrit links.)

https://chromium-review.googlesource.com/c/chromium/src/+/7453440

2. Has this fix been verified on Canary to not pose any stability regressions?

Yes.
The change is included in 146.0.7636.0 and 16557.0.0.

2. Does this fix pose any potential non-verifiable stability risks?

I do not think so.

3. Does this fix pose any known compatibility risks?

Yes.
This brings the behavior change following the specification change in https://github.com/whatwg/fetch/pull/1907.
If there is a Web page expecting Status 416 for the opaque range request, which is usable for XS-leak, it breaks.

4. Does it require manual verification by the test team? If so, please describe required testing.

Unfortunately, yes.  Please follow the reproduction case in #comment1 to ensure the behavior change.
I should have written a Web platform test for this as Anne asked in https://github.com/whatwg/fetch/issues/1906.

5. (no answer required) Please check the OS custom field to ensure all impacted OSes are checked!

sure.  

### ch...@google.com (2026-01-16)

**Merge approved:** your change passed merge requirements and is auto-approved for M145. Please go ahead and merge the CL to branch 7632 (refs/branch-heads/7632) manually. Please contact milestone owner if you have questions.
Merge instructions: <https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/docs/process/merge_request.md>
Owners: andywu (ChromeOS), srinivassista (Desktop US), None (Desktop EMEA), harrysouders (Mobile US), eakpobaro (Mobile EMEA)

### ch...@google.com (2026-01-16)

Merge review required: M144 is already shipping to stable.

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
Owners: alonbajayo (ChromeOS), srinivassista (Desktop US), None (Desktop EMEA), govind (Mobile US), eakpobaro (Mobile EMEA)

### yy...@chromium.org (2026-01-16)

1. Why does your merge fit within the merge criteria for these milestones?

This is a security issue cthomp@ asked us to fix. (See #comment2)

2. What changes specifically would you like to merge? Please link to Gerrit.

https://chromium-review.googlesource.com/c/chromium/src/+/7453440

3. Have the changes been released and tested on canary?

Yes.
The change is included in 146.0.7636.0 and 16557.0.0.

4. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?

No.  However, this fix is backed by the finch flag. kBlockPartialResponseWithoutRange

5. [Chrome OS only]: Was the change reviewed and approved by the Eng Prod Representative? https://goto.google.com/cros-engprodcomponents

no.

6. If this merge addresses a major issue in the stable channel, does it require manual verification by the test team? If so, please describe required testing.

Unfortunately, yes.  Please follow the reproduction case in #comment1 to ensure the behavior change.
I should have written a Web platform test for this as Anne asked in https://github.com/whatwg/fetch/issues/1906.

### dx...@google.com (2026-01-16)

Project: chromium/src  

Branch:  refs/branch-heads/7632  

Author:  Yoshisato Yanagisawa [yyanagisawa@chromium.org](mailto:yyanagisawa@chromium.org)  

Link:    <https://chromium-review.googlesource.com/7488315>

[M145] Block opaque 416 responses to non-range requests

---


Expand for full commit details
```
     
    Extend the security check for opaque 206 responses to also cover 
    416 responses when the request does not contain a Range header. This 
    makes the handling of these responses symmetric. 
     
    This change is controlled by the 'kBlockPartialResponseWithoutRange' 
    feature flag. 
     
    See: https://github.com/whatwg/fetch/issues/1906 
     
    (cherry picked from commit c0e8cebca540579fa734bbca6ffc1e280982857f) 
     
    Bug: 474435504 
    Change-Id: Ifbc4b9b9ea9f45ef6b5a0d3705de5368a1ee0227 
    Reviewed-on: https://chromium-review.googlesource.com/c/chromium/src/+/7453440 
    Reviewed-by: Takashi Toyoshima <toyoshim@chromium.org> 
    Commit-Queue: Yoshisato Yanagisawa <yyanagisawa@chromium.org> 
    Cr-Original-Commit-Position: refs/heads/main@{#1569484} 
    Reviewed-on: https://chromium-review.googlesource.com/c/chromium/src/+/7488315 
    Commit-Queue: Takashi Toyoshima <toyoshim@chromium.org> 
    Auto-Submit: Yoshisato Yanagisawa <yyanagisawa@chromium.org> 
    Cr-Commit-Position: refs/branch-heads/7632@{#216} 
    Cr-Branched-From: 0bbdf2913883391365383b0a5dfe7bf9fd1a5213-refs/heads/main@{#1568190}

```

---

Files:

- M `third_party/blink/common/features.cc`
- M `third_party/blink/public/common/features.h`
- M `third_party/blink/renderer/platform/loader/fetch/resource_loader.cc`
- M `third_party/blink/renderer/platform/loader/fetch/resource_loader_test.cc`

---

Hash: [a7d1ef58edc81c53ba4f336cb67eba6325bbe09c](https://chromiumdash.appspot.com/commit/a7d1ef58edc81c53ba4f336cb67eba6325bbe09c)  

Date: Fri Jan 16 11:49:43 2026


---

### ch...@google.com (2026-01-19)

This issue has been approved for a merge. Please merge the fix to any appropriate branches as soon as possible!

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.

### dr...@chromium.org (2026-01-20)

Approved for merge to M144. There's only one Canary crash (crash/5b7ddee524bfc87c) in the affected function, and it looks unrelated.

### pe...@google.com (2026-01-20)

LTS Milestone M138

This issue has been flagged as a merge candidate for Chrome OS' LTS channel. If selected, our merge team will handle any additional merges. To help us determine if this issue requires a merge to LTS, please answer this short questionnaire:

1. Was this issue a regression for the milestone it was found in?
2. Is this issue related to a change or feature merged after the latest LTS Milestone?

### ch...@google.com (2026-01-21)

Dear owner, thanks for fixing this bug. We've reopened it because:

- It is not clear which CLs have ‘fixed’ (=required to consider the bug resolved; e.g. not logging) this bug. Please fill in the “Fixed By Code Changes” field with the appropriate Gerrit url to disambiguate using the following guidelines:
  - If there are multiple CLs required, please list all.
  - If the fix landed in a third party library (v8, Dawn, etc), please list the third party commits - not the rolls.
  - If there are cherrypicks or back merges, please list the original commits which landed on HEAD.
  - If there is no relevant Gerrit link (i.e. the fix does not live in or roll into Chromium), please use the value ‘NA’.
  - If this is a non-browser ChromeOS-specific bug, please move it to component 1335705 in the Google issue tracker.
  - If this field requires human intervention for some reason, please add this bug to the hotlist id 6265590.
    After resolving the above issue(s), this bug can be marked closed again. Thanks for your time!

### yy...@chromium.org (2026-01-21)

Re: #comment17
1. Was this issue a regression for the milestone it was found in?

No.
This might have existed since the code has originally implemented as #comment1 mentioned.

2. Is this issue related to a change or feature merged after the latest LTS Milestone?

No.
As told in the answer to 1., it should be the long running xs-leak.

### yy...@chromium.org (2026-01-21)

I have added the “Fixed By Code Changes” field to address #comment18.

### yy...@chromium.org (2026-01-21)

Also note that the spec has already been updated:
https://github.com/whatwg/fetch/issues/1906
https://github.com/whatwg/fetch/pull/1907

WebKit fix:
https://github.com/annevk/WebKit/commit/0e32f9cb18b8b73565a207e5fb616bc02fe5b6dc

WebKit seems to add the new WPT but it looks not show up in the site yet?
https://wpt.fyi/results/fetch/range?label=master&label=experimental&aligned&q=fetch%2Frange

### pe...@google.com (2026-01-21)

This issue requires additional review before it can be merged to the LTS channel. Please answer the following questions to help us evaluate this merge:

1. Number of CLs needed for this fix and links to them.
2. Level of complexity (High, Medium, Low - Explain)
3. Has this been merged to a stable release? beta release?
4. Overall Recommendation (Yes, No)

### qk...@google.com (2026-01-21)

1. <https://chromium-review.googlesource.com/c/chromium/src/+/7501275>
2. Low - There was a trivial conflict.
3. 144 and 145
4. Yes, According to the description, this issue was introduced by <https://chromium-review.googlesource.com/c/chromium/src/+/2339761> (merged in 2020), and M138 has the CL.

### yy...@chromium.org (2026-01-21)

deleted

### dx...@google.com (2026-01-21)

Project: chromium/src  

Branch:  refs/branch-heads/7559  

Author:  Yoshisato Yanagisawa [yyanagisawa@chromium.org](mailto:yyanagisawa@chromium.org)  

Link:    <https://chromium-review.googlesource.com/7501315>

[M144] Block opaque 416 responses to non-range requests

---


Expand for full commit details
```
     
    Extend the security check for opaque 206 responses to also cover 
    416 responses when the request does not contain a Range header. This 
    makes the handling of these responses symmetric. 
     
    This change is controlled by the 'kBlockPartialResponseWithoutRange' 
    feature flag. 
     
    See: https://github.com/whatwg/fetch/issues/1906 
     
    (cherry picked from commit c0e8cebca540579fa734bbca6ffc1e280982857f) 
     
    Bug: 474435504 
    Change-Id: Ifbc4b9b9ea9f45ef6b5a0d3705de5368a1ee0227 
    Reviewed-on: https://chromium-review.googlesource.com/c/chromium/src/+/7453440 
    Reviewed-by: Takashi Toyoshima <toyoshim@chromium.org> 
    Commit-Queue: Yoshisato Yanagisawa <yyanagisawa@chromium.org> 
    Cr-Original-Commit-Position: refs/heads/main@{#1569484} 
    Reviewed-on: https://chromium-review.googlesource.com/c/chromium/src/+/7501315 
    Auto-Submit: Yoshisato Yanagisawa <yyanagisawa@chromium.org> 
    Commit-Queue: Takashi Toyoshima <toyoshim@chromium.org> 
    Cr-Commit-Position: refs/branch-heads/7559@{#3794} 
    Cr-Branched-From: 223dfbac1c7542a06b422390d954afe5b560b607-refs/heads/main@{#1552494}

```

---

Files:

- M `third_party/blink/common/features.cc`
- M `third_party/blink/public/common/features.h`
- M `third_party/blink/renderer/platform/loader/fetch/resource_loader.cc`
- M `third_party/blink/renderer/platform/loader/fetch/resource_loader_test.cc`

---

Hash: [94c314c8d814c2dba147e9a8e92601d2fe4f5942](https://chromiumdash.appspot.com/commit/94c314c8d814c2dba147e9a8e92601d2fe4f5942)  

Date: Wed Jan 21 12:31:51 2026


---

### an...@google.com (2026-01-23)

Waiting for it to soak in M144 Stable. 

### wf...@chromium.org (2026-01-26)

was this merged to 145?

### sp...@google.com (2026-01-26)

** NOTE: This is an automatically generated email **

Hello,

Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $3000.00 for this report.

Rationale for this decision:
Baseline / Lower Impact user information disclosure plus a bisect bonus


Important: If you aren't already registered with Google as a supplier, p2p-vrp@google.com will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.

If you have any payment related requests, please direct them to p2p-vrp@google.com. Please remember to include the subject of this email and the email address that the report was sent from.


Thank you for your efforts and helping us make Chrome more secure for all users!

Cheers,
Chrome VRP Panel Bot


P.S. One other thing we'd like to mention:

* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.

Please contact security-vrp@chromium.org with any questions.

### yy...@chromium.org (2026-01-27)

Re: #comment27
It has been merged to M145 in https://chromium-review.googlesource.com/7488315
I am not sure if it has been released or not.

### dx...@google.com (2026-03-10)

Project: chromium/src  

Branch:  refs/branch-heads/7204  

Author:  Yoshisato Yanagisawa [yyanagisawa@chromium.org](mailto:yyanagisawa@chromium.org)  

Link:    <https://chromium-review.googlesource.com/7501275>

[M138-LTS] Block opaque 416 responses to non-range requests

---


Expand for full commit details
```
     
    Extend the security check for opaque 206 responses to also cover 
    416 responses when the request does not contain a Range header. This 
    makes the handling of these responses symmetric. 
     
    This change is controlled by the 'kBlockPartialResponseWithoutRange' 
    feature flag. 
     
    See: https://github.com/whatwg/fetch/issues/1906 
     
    (cherry picked from commit c0e8cebca540579fa734bbca6ffc1e280982857f) 
     
    Bug: 474435504 
    Change-Id: Ifbc4b9b9ea9f45ef6b5a0d3705de5368a1ee0227 
    Reviewed-on: https://chromium-review.googlesource.com/c/chromium/src/+/7453440 
    Reviewed-by: Takashi Toyoshima <toyoshim@chromium.org> 
    Commit-Queue: Yoshisato Yanagisawa <yyanagisawa@chromium.org> 
    Cr-Original-Commit-Position: refs/heads/main@{#1569484} 
    Reviewed-on: https://chromium-review.googlesource.com/c/chromium/src/+/7501275 
    Reviewed-by: Yoshisato Yanagisawa <yyanagisawa@chromium.org> 
    Commit-Queue: Gyuyoung Kim (xWF) <qkim@google.com> 
    Reviewed-by: Artem Sumaneev <asumaneev@google.com> 
    Owners-Override: Artem Sumaneev <asumaneev@google.com> 
    Cr-Commit-Position: refs/branch-heads/7204@{#3501} 
    Cr-Branched-From: d5de512dc9dc8ddfe4e6d71b0637578bb6158683-refs/heads/main@{#1465706}

```

---

Files:

- M `third_party/blink/common/features.cc`
- M `third_party/blink/public/common/features.h`
- M `third_party/blink/renderer/platform/loader/fetch/resource_loader.cc`
- M `third_party/blink/renderer/platform/loader/fetch/resource_loader_test.cc`

---

Hash: [fdfa25293f77e25b3c953ec82eceaea39383173b](https://chromiumdash.appspot.com/commit/fdfa25293f77e25b3c953ec82eceaea39383173b)  

Date: Tue Mar 10 04:02:22 2026


---

### ch...@google.com (2026-04-30)

This bug has been closed for more than 14 weeks. Removing issue access restrictions.

## Bounty Award

> Baseline / Lower Impact user information disclosure plus a bisect bonus

---
*Data from [Chromium Issue Tracker](https://issues.chromium.org/issues/474435504)*
