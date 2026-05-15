# [Critical] Unresolved Google Bugs Leak 

| Field | Value |
|-------|-------|
| **Issue ID** | [472921872](https://issues.chromium.org/issues/472921872) |
| **Status** | Fixed |
| **Severity** | S3-Low |
| **Priority** | P3 |
| **Component** | Unknown |
| **Reporter** | am...@gmail.com |
| **Assignee** | dr...@chromium.org |
| **Created** | 2026-01-02 |
| **Bounty** | $5,000.00 |

## Description

**Summary:** [Critical] Unresolved Google Bugs Leak

**Program:** Google VRP

**Vulnerability type:** Other

### Details

**Vulnerability Description**
Issue child (say 2) marked as duplicate of issue parent(say 1), parent [issue 1](https://issues.chromium.org/issues/1) is still unresolved but after 14 weeks [issue 2](https://issues.chromium.org/issues/2) became public with poc details available in the duplicated report, Which allows attacker to exploit the issue on latest

It literaly exposes unresolved bugs to internet publicly

**Attack Preconditions**
There is no such.

**Reproduction Steps / POC**
Just check the google bugbounty portal for recently disclosed bugs

Eg: <https://issues.chromium.org/issues/416417887>

this issue was reported by me earlier to chrome but marked as duplicate but still the original issue is not made public yet (unresolved), it contains poc and other technical details too, but now the issue is public and everyone have access into it

### Attack scenario

Exploitation of unresolved bugs on google customers (eg: chrome, chrome os, AI etc)

## Timeline

### sp...@google.com (2026-01-02)

*NOTE: This is an automatically generated email*

Hi! Many thanks for sharing your report.

IMPORTANT: During the holidays (December 22 to January 5), our team might take
longer than usual to process the reports. Thank you for your understanding.

This email confirms we've received your message. We'll investigate the issue you've reported and get back to you once we have an update. In the meantime, you might want to take a look at the [list of frequently asked questions about Google Bug Hunters](https://bughunters.google.com/about/4925519884451840/frequently-asked-questions).

Also, if you have not already done so, create a profile on [the Google Bughunters site](https://bughunters.google.com/) if you'd like us to publicly recognize your contribution:

- [Leaderboard](https://bughunters.google.com/leaderboard) – You'll be added here if we issue a reward for your report.
- [Honorable Mentions](https://bughunters.google.com/leaderboard/honorable-mentions) – You'll be added here if you are not in the Hall of Fame, but we file a security vulnerability bug based on your report.

**Note that we only act on reports concerning vulnerabilities or technical security problems in one of our products. This is not the correct channel if you need to resolve a problem with your account, or want to report non-security bugs or suggest a new product feature.**

Good news! According to Google magic, your report is likely actionable for us, so it has been moved up in our queue by raising the priority. The next step is human expert review, which should happen slightly sooner now.

Cheers,   

Google Security Bot

[Follow us](https://twitter.com/googlevrp) on Twitter!

### am...@gmail.com (2026-01-02)

Solution:

Duplicated bugs should be made public only after the parent issue is closed / during parent issue disclose

### ...@google.com (2026-01-06)

This report may qualify for the [Chrome Vulnerability Reward Program](https://bughunters.google.com/about/rules/chrome-friends/5745167867576320/chrome-vulnerability-reward-program-rules). We are moving this report to the Chromium issue tracker.

### dr...@chromium.org (2026-01-06)

Thank you for reporting this to us! This is indeed a bug in our internal automation. For the internal work, I've filed <http://b/473887895>.

### am...@gmail.com (2026-01-07)

Thanks for the update team, Kindly update the priority and severity for this case. It needs immediate attention to avoid exposing bugs publicly before patching

### dr...@chromium.org (2026-01-07)

Okay I have fixed our automation and closed down any bugs that I found open. If you're aware of any bugs that are still open, please let me know. But I think this is fixed.

### dr...@chromium.org (2026-01-07)

Note that this bug doesn't really fit into our severity guidelines, but since it's a fixed security bug it will go to the VRP panel.

### ch...@google.com (2026-01-07)

Dear owner, thanks for fixing this bug. We've reopened it because:

- Security bugs need the Severity (S0-S3) and the Found In set, which will enable the bots to request merges to the correct branches (as well as helping out our vulnerability reward and CVE processes). Please consult with any Chrome security contact ([security@chromium.org](mailto:security@chromium.org)) to arrange to set these labels. Severity guidelines: <https://chromium.googlesource.com/chromium/src/+/refs/heads/main/docs/security/severity-guidelines.md#severity-guidelines-for-security-issues> FoundIn guidelines: <https://chromium.googlesource.com/chromium/src/+/main/docs/security/security-labels.md#labels-relevant-for-any-type_bug_security>
  After resolving the above issue(s), this bug can be marked closed again. Thanks for your time!

### dr...@chromium.org (2026-01-07)

There's nothing to merge here, so setting a dummy severity and Impact-None.

### am...@gmail.com (2026-01-08)

> Note that this bug doesn't really fit into our severity guidelines, (Comment 8)

Hope it is a critical data exposure area, though it is not under chrome vrp guideliness it will surely be under google vrp for those exposure

So anyway instead of moving forth the issues to another tracker i request your team to award the bounty in this ticket itself to avoid any additional efforts

Thanks

### am...@gmail.com (2026-01-21)

Any update on bounty, Team?

### dr...@chromium.org (2026-01-28)

It was pointed out to me that I never gave a clear public description of the impact of this bug.

When a bug is marked as a duplicate, we should open it to the public only when the canonical bug is public. Instead, we were opening duplicates when the canonical bug is marked fixed. No unfixed vulnerabilities were leaked due to this bug. But this does increase our patch gap risk. Normally an attacker would have to figure out the exploit from the fix commit alone, but now they can get a head start with a PoC and some thoughts from the reporter/engineers.

### wf...@chromium.org (2026-01-30)

The VRP panel thanks you for your report. This was a slightly unorthodox report for us to assess as it's in our infrastructure not the client, however we were able to use the values from the main Google program to guide us here <https://bughunters.google.com/about/rules/google-friends/google-and-alphabet-vulnerability-reward-program-vrp-rules> and feel the reward given is appropriate given that this issue only allowed limited access to duplicate bugs once the issue had been fixed (similar to just reading the commit, which was already public). Thanks for finding this issue though, we very much appreciate it!

### sp...@google.com (2026-01-30)

** NOTE: This is an automatically generated email **

Hello,

Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $5000.00 for this report.

Rationale for this decision:
Limited information leak on a tier 0 site


Important: This payment will be issued by Bugcrowd. You will receive an email from Bugcrowd in the next 24 hours which contains a submission you must claim to be rewarded.

If you do not receive an email from them, please check your spam folder and then reach out to us via a comment here. For issues related to Bugcrowd itself, please contact them via https://bugcrowd.com/support.


Thank you for your efforts and helping us make Chrome more secure for all users!

Cheers,
Chrome VRP Panel Bot


P.S. One other thing we'd like to mention:

* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.

Please contact security-vrp@chromium.org with any questions.

### ch...@google.com (2026-04-16)

This bug has been closed for more than 14 weeks. Removing issue access restrictions.

## Bounty Award

> Limited information leak on a tier 0 site

---
*Data from [Chromium Issue Tracker](https://issues.chromium.org/issues/472921872)*
