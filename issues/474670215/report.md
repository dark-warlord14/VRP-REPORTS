# Bypass for console.log %c formatter url filter

| Field | Value |
|-------|-------|
| **Issue ID** | [474670215](https://issues.chromium.org/issues/474670215) |
| **Status** | Assigned |
| **Severity** | S3-Low |
| **Priority** | P3 |
| **Component** | Platform>DevTools>Console |
| **Platforms** | Linux, Mac, Windows, ChromeOS |
| **Reporter** | re...@gmail.com |
| **Assignee** | pf...@google.com |
| **Created** | 2026-01-10 |
| **Bounty** | $1,000.00 |

## Description

**VULNERABILITY DETAILS**  

The mitigations for [Issue 40056332](https://issues.chromium.org/issues/40056332) and [Issue 40060475](https://issues.chromium.org/issues/40060475) can be bypassed by using specific CSS syntax to load an external url. This leads to minor data exfil in DevTools (ip/ua/headers, whether the console was opened, css media queries etc).

The vulnerable regex is at: <https://source.chromium.org/chromium/_/chromium/devtools/devtools-frontend/+/main:front_end/panels/console/ConsoleFormat.ts;l=206;drc=8cf3f6e6e069efefa0ae8ef9557214f62e856f81>

**VERSION**  

Chrome Version: 145.0.7587.6 Dev, 145.0.7626.0 Canary  

Operating System: Windows, Mac, Linux, ChromeOS

**REPRODUCTION CASE**  

PoC:

```
console.log("%c\t", `background-image:if(supports(_): "url(data:"; else: url("https://google.com/favicon.ico"));`)

```

Running the above, the Google favicon will appear in the DevTools console log.

**CREDIT INFORMATION**  

Externally reported security bugs may appear in Chrome release notes. If this bug is included, how would you like to be credited?  

Reporter credit: Lyra Rebane (rebane2001)

## Attachments

- [chrome_2026-01-10_15-16-19.png](attachments/chrome_2026-01-10_15-16-19.png) (image/png, 3.5 KB)
- [0001-console-improve-url-regex.patch](attachments/0001-console-improve-url-regex.patch) (text/x-diff, 2.2 KB)
- [index.html](attachments/index.html) (text/html, 134 B)
- [chrome_2026-01-12_20-59-10.mp4](attachments/chrome_2026-01-12_20-59-10.mp4) (video/mp4, 232.4 KB)

## Timeline

### re...@gmail.com (2026-01-10)

A simple fix here would be to change the regex from `/url\([\'\"]?([^\)]*)/g` to `/(?=url\([\'\"]?([^\)]*))/g`.

However, this would still leave the regex vulnerable to some slightly modified PoCs:

```
// URL is uppercase, it does not get converted to lowercase because of the if statement
console.log("%c\t", `background-image:if(supports(_): "url(data:"; else: URL("https://google.com/favicon.ico"));`)

```
```
// the l in url is escaped, it stays escaped because of the if statement
console.log("%c\t", `background-image:if(supports(_): "url(data:"; else: ur\\6c ("https://google.com/favicon.ico"));`)

```

For a proper fix we'd have to write a regex that's case-insensitive and can also deal with escapes, which I wrote here:

```
(?=                                // try regex at every char, so nesting url()s is fine
  (?:\\0{0,4}[57]5[ \n\t]?|u)      // uU (or its escapes)
  (?:\\0{0,4}[57]2[ \n\t]?|r)      // rR (or its escapes)
  (?:\\0{0,4}[46]c[ \n\t]?|l)      // lL (or its escapes)
  (?:\\0{0,4}28[ \n\t]?|\()        // ( (or its escapes)
  (?:\\0{0,4}2[27][ \n\t]?|\'|\")? // optionally, single/double-quotes or their escapes
  ([^\)]*)                         // match until ) (we don't need to worry about escapes here)
)

```

Which, in code, would be:

```
const URL_REGEX = /(?=(?:\\0{0,4}[57]5[ \n\t]?|u)(?:\\0{0,4}[57]2[ \n\t]?|r)(?:\\0{0,4}[46]c[ \n\t]?|l)(?:\\0{0,4}28[ \n\t]?|\()(?:\\0{0,4}2[27][ \n\t]?|\'|\")?([^\)]*))/gi;

```

This *should* take care of all possible escape edge-cases [based on the CSS spec](https://www.w3.org/TR/css-syntax-3/#consume-escaped-code-point).

While you can use comments within the if statement, I don't think there's any way to actually bypass this regex using comments.

The important part of the match is `url(`, so the rest of it (`'"` and `)`) doesn't need to be as robust because we're just allow-listing the `data:` protocol.

---

I would like to submit this fix as a Chromium patch myself, please let me know if it's okay to go ahead and do so.

### re...@gmail.com (2026-01-10)

I've attached my patch for my CL. Please let me know if/when it's okay to upload to Gerrit.

---

```
[console] Improve URL regex for console.log %c formatter

This CL improves upon the URL regex of the %c formatter to prevent some
new `url()` edge-cases in modern CSS.

The CL also adds the corresponding test cases.

Bug: 474670215

```

### re...@gmail.com (2026-01-10)

It just occurred to me that image-set could be used for a bypass as well - I'll add it to my CL once I can put it on Gerrit.

### ct...@chromium.org (2026-01-12)

Thank you for the report! I can repro this on Chrome Stable and Canary if I paste the string into the DevTools console directly, but I have not been able to reproduce this from a <script> tag on the site itself (testing using local overrides on <https://example.com>). Have you been able to trigger this via JS on a site?

Passing this to DevTools folks from the earlier bugs. I believe they would gladly review a fix CL if you would like to upload one.

Setting some security labels and assigning this to bmeurer@ as we like to have all security bugs owned by project members.

### re...@gmail.com (2026-01-12)

I can repro from a script tag on my own website too: <https://lyra.horse/f/tmp/e6b30ccc8de61c6d/index.html>

Does your local overrides script tag otherwise work with console.log?

Attached is the html file used and a video showing the repro.

### ct...@chromium.org (2026-01-12)

Thank you, yes that repros for me. I was trying to be quick using local overrides but it looks like it just doesn't work, while a real live site does :-)

### re...@gmail.com (2026-01-12)

On the topic of image-set, I'm not actually sure what the best approach would be.

This is because these are all valid bypasses:

```
/* basic usage, easy to regex */
background-image:if(else: image-set("http://...") )
/* multiple images */
background-image:if(else: image-set("data:..." 8x, "http://..." 4x) )
/* parenthesis confusion 1 */
background-image:if(else: image-set("data:...\")" 8x, "http://..." 4x) )
/* parenthesis confusion 2 */
background-image:if(else: image-set("data:..." type("\")"), "http://..." type("image/png")) )
/* variables */
background-image:if(else: image-set(var(--x, "http://...") 4x) )

```

The main trouble with image-set is that it allows you to use multiple quoted strings for the URLs instead of using `url()`.

---

One solution would be to apply a strict regex to all quoted values if an `image-set` is found.

Here's a quick draft I wrote:

```
// greedy image-set regex, s for dotall
// ideally this would be similar to the URL_REGEX 
const IMAGESET_REGEX = /image-set\((.*)\)/gis;
// NOT a real regex, illustrative
const QUOTE_REGEX = /(['"])(\1|[^\1]+)/g;

const imageSetValue = IMAGESET_REGEX.exec(value);
if (imageSetValue) {
   const potentialUrls = [...imageSetValue[1].matchAll(QUOTE_REGEX)].map(match => match[2]);
   // do the usual url checks...
}

```

But the problem with this is that the `QUOTE_REGEX` would need to be properly written (to handle backslashes and strings such as `"'"`) and it's possible that this implementation would end up being vulnerable to DoS, allowing for a malicious site to disable DevTools. It would also be harder to maintain.

So I don't think this would be a good solution.

---

A very simple solution would be to just ban image-sets from being used in the %c formatter styles, which I think would be the best security and implementation wise, but it does mean the feature simply couldn't be used.

Anyways I'd love to hear feedback on what we could do with the image-set edge-case.

### bm...@google.com (2026-01-13)

Thanks for the report, and the patches. @re...@gmail.com please go ahead with uploading a CL to Gerrit.

@pf...@google.com please review and assist in landing the fix. Also please double-check regarding edge-cases in the CSS spec.

### re...@gmail.com (2026-01-15)

I've been brainstorming this for a while, and I think I came up with a pretty good solution to the image-set problem, which is using an allowed syntax regex.

Here's a little draft I made (I wrote this on my phone so there might be obvious mistakes I'll clear up later):

```
// Final version would also match character escapes
const IMAGE_SET_REGEX = /image-set(.*/gi;
// Match only image-set that has url()s with no quote/escape shenanigans
const GOOD_IMAGE_SET_REGEX = /^image-set\((?:(?:(?:url|type)\("[^\\"]+"\)|\d+x),?\s*)+)/i;

// Make sure every image-set matches the good regex
if([...value.matchAll(IMAGE_SET_REGEX)].some(match => !GOOD_IMAGE_SET_REGEX.exec(match[0])))
    return false;

// Check url()s as usual

```

I think this is a pretty good solution, as it covers most benign use cases.

So if a developer were to write:

```
background: image-set( "data:...", 'data:...' 2x , "data:..." type("image/webp"));

```

it would parse into:

```
background: image-set(url("data:...") 1x, url("data:...") 2x, url("data:...") 1x type("image/webp"));

```

and match the allowed regex.

And the allowed regex enforces only image-sets that use url()s, so the usual url() filter can take care of the rest.

### re...@gmail.com (2026-01-15)

I also found another CSS edge-case - `\u\r\l()` still loads the image. I'll cover that too.

### re...@gmail.com (2026-01-15)

I added fixes for [comment#8](https://issues.chromium.org/issues/474670215#comment8) [comment#10](https://issues.chromium.org/issues/474670215#comment10) [comment#11](https://issues.chromium.org/issues/474670215#comment11), cleaned up the code, and uploaded the CL:  

<https://chromium-review.googlesource.com/c/devtools/devtools-frontend/+/7484749>

### dx...@google.com (2026-01-27)

Project: devtools/devtools-frontend  

Branch:  main  

Author:  Lyra Rebane [rebane2001@gmail.com](mailto:rebane2001@gmail.com)  

Link:    <https://chromium-review.googlesource.com/7484749>

[console] Improve URL filtering for console.log %c formatter

---


Expand for full commit details
```
     
    This CL improves upon the URL regex of the %c formatter to prevent some 
    new `url()` and `image-set()` edge-cases in modern CSS. Specifically, it 
    covers cases where said CSS functions are escaped, and those where 
    `image-set()` is used without using `url()`; 
     
    The CL also adds the corresponding test cases. 
     
    Bug: 474670215 
    Change-Id: I21909a2650c985eac4f2ec714aea561e5d840003 
    Reviewed-on: https://chromium-review.googlesource.com/c/devtools/devtools-frontend/+/7484749 
    Commit-Queue: Simon Zünd <szuend@chromium.org> 
    Reviewed-by: Simon Zünd <szuend@chromium.org> 
    Reviewed-by: Philip Pfaffe <pfaffe@chromium.org>

```

---

Files:

- M `AUTHORS`
- M `front_end/panels/console/ConsoleFormat.test.ts`
- M `front_end/panels/console/ConsoleFormat.ts`

---

Hash: [a98136b97706f7972cbc99b69e283398d90a442c](https://chromiumdash.appspot.com/commit/a98136b97706f7972cbc99b69e283398d90a442c)  

Date: Thu Jan 22 08:31:20 2026


---

### re...@gmail.com (2026-01-27)

Should be fixed now ^.^

### pf...@google.com (2026-01-27)

Thanks for the report and the fix!

### ch...@google.com (2026-01-27)

Dear owner, thanks for fixing this bug. We've reopened it because:

- It is not clear which CLs have ‘fixed’ (=required to consider the bug resolved; e.g. not logging) this bug. Please fill in the “Fixed By Code Changes” field with the appropriate Gerrit url to disambiguate using the following guidelines:
  - If there are multiple CLs required, please list all.
  - If the fix landed in a third party library (v8, Dawn, etc), please list the third party commits - not the rolls.
  - If there are cherrypicks or back merges, please list the original commits which landed on HEAD.
  - If there is no relevant Gerrit link (i.e. the fix does not live in or roll into Chromium), please use the value ‘NA’.
  - If this is a non-browser ChromeOS-specific bug, please move it to component 1335705 in the Google issue tracker.
  - If this field requires human intervention for some reason, please add this bug to the hotlist id 6265590.
    After resolving the above issue(s), this bug can be marked closed again. Thanks for your time!

### dx...@google.com (2026-01-27)

Project: chromium/src  

Branch:  main  

Author:  chromium-autoroll [chromium-autoroll@skia-public.iam.gserviceaccount.com](mailto:chromium-autoroll@skia-public.iam.gserviceaccount.com)  

Link:    <https://chromium-review.googlesource.com/7520505>

Roll DevTools Frontend from d7036cc0b4fe to a98136b97706 (1 revision)

---


Expand for full commit details
```
     
    https://chromium.googlesource.com/devtools/devtools-frontend.git/+log/d7036cc0b4fe..a98136b97706 
     
    2026-01-27 rebane2001@gmail.com [console] Improve URL filtering for console.log %c formatter 
     
    If this roll has caused a breakage, revert this CL and stop the roller 
    using the controls here: 
    https://autoroll.skia.org/r/devtools-frontend-chromium 
    Please CC chrome-devtools-staff+oncall-change@google.com,liviurau@google.com on the revert to ensure that a human 
    is aware of the problem. 
     
    To report a problem with the AutoRoller itself, please file a bug: 
    https://issues.skia.org/issues/new?component=1389291&template=1850622 
     
    Documentation for the AutoRoller is here: 
    https://skia.googlesource.com/buildbot/+doc/main/autoroll/README.md 
     
    Bug: chromium:474670215 
    Change-Id: Ia7c60032842b79172f0550361570f7f38fa718fd 
    Reviewed-on: https://chromium-review.googlesource.com/c/chromium/src/+/7520505 
    Bot-Commit: chromium-autoroll <chromium-autoroll@skia-public.iam.gserviceaccount.com> 
    Commit-Queue: chromium-autoroll <chromium-autoroll@skia-public.iam.gserviceaccount.com> 
    Cr-Commit-Position: refs/heads/main@{#1575109}

```

---

Files:

- M `DEPS`
- M `third_party/devtools-frontend/src`

---

Hash: [97d9cd6f35ce36101d801e94c0e207b2fe4bd085](https://chromiumdash.appspot.com/commit/97d9cd6f35ce36101d801e94c0e207b2fe4bd085)  

Date: Tue Jan 27 11:25:40 2026


---

### re...@gmail.com (2026-01-27)

I guess the issue was that the roll CL wasn't merged yet, so should be fixed now that it is merged?

### ya...@google.com (2026-01-27)

Philip, does this need a back merge?

### pf...@google.com (2026-01-27)

For security issues the security team decides on merges, so we should usually just wait for them to make a call.

### sp...@google.com (2026-02-20)

** NOTE: This is an automatically generated email **

Hello,

Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $1000.00 for this report.

Rationale for this decision:
Low impact user information disclosure plus a patch bonus


Important: This payment will be issued by Bugcrowd. You will receive an email from Bugcrowd in the next 24 hours which contains a submission you must claim to be rewarded.

If you do not receive an email from them, please check your spam folder and then reach out to us via a comment here. For issues related to Bugcrowd itself, please contact them via https://bugcrowd.com/support.


Thank you for your efforts and helping us make Chrome more secure for all users!

Cheers,
Chrome VRP Panel Bot


P.S. One other thing we'd like to mention:

* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.

Please contact security-vrp@chromium.org with any questions.

### ch...@google.com (2026-05-06)

This bug has been closed for more than 14 weeks. Removing issue access restrictions.

## Bounty Award

> Low impact user information disclosure plus a patch bonus

---
*Data from [Chromium Issue Tracker](https://issues.chromium.org/issues/474670215)*
