# Privileged `chrome://` navigation via reload-triggered server redirect in iOS Chrome

| Field | Value |
|-------|-------|
| **Issue ID** | [476898368](https://issues.chromium.org/issues/476898368) |
| **Status** | Assigned |
| **Severity** | S3-Low |
| **Priority** | P2 |
| **Component** | UI>Browser>Navigation |
| **Platforms** | iOS |
| **Reporter** | po...@gmail.com |
| **Assignee** | ol...@google.com |
| **Created** | 2026-01-19 |
| **Bounty** | $1,000.00 |

## Description

---

### Report description

Privileged `chrome://` navigation via reload-triggered server redirect in iOS Chrome

---

### Bug location

#### Where do you want to report your vulnerability?

Chrome VRP – Report security issues affecting the Chrome browser. [See program rules](https://bughunters.google.com/about/rules/5745167867576320/chrome-vulnerability-reward-program-rules)

#### Which URL (or repository) have you found the vulnerability in?

<https://chromium.googlesource.com/chromium/src/>

---

### The problem

#### Please describe the technical details of the vulnerability

On iOS, Chrome embeds Chromium's `ios/web` navigation stack on top of `WKWebView`. The navigation delegate class `CRWWKNavigationHandler` contains special handling for "app-specific" URLs, which in the iOS Chrome configuration include internal `chrome://` WebUI pages such as `chrome://flags/`.

The decision for whether to allow an app-specific navigation is implemented in `ios/web/navigation/crw_wk_navigation_handler.mm`:

```
- (BOOL)shouldAllowAppSpecificURLNavigationAction:(WKNavigationAction*)action
                                       transition:
                                           (ui::PageTransition)pageTransition {
  GURL requestURL = net::GURLWithNSURL(action.request.URL);
  DCHECK(web::GetWebClient()->IsAppSpecificURL(requestURL));
  web::NavigationItem* lastItem =
      self.webStateImpl->GetNavigationManager()->GetLastCommittedItem();
  if (lastItem &&
      (web::GetWebClient()->IsAppSpecificURL(lastItem->GetVirtualURL()) ||
       web::GetWebClient()->IsAppSpecificURL(lastItem->GetURL()))) {
    // Last committed page is also app specific and navigation should be
    // allowed.
    return YES;
  }

  if (pageTransition & ui::PAGE_TRANSITION_FORWARD_BACK) {
    // Allow back-forward navigations.
    return YES;
  }

  if (pageTransition & ui::PAGE_TRANSITION_RELOAD) {
    // Allow reload navigations.
    return YES;
  }

  // ... user-typed / bookmark and iframe cases omitted ...
  return NO;
}

```

For an `app-specific` URL (such as a `chrome://` page), the function unconditionally allows the navigation when the page transition has the `PAGE_TRANSITION_RELOAD` bit set, even if the last committed page was a regular web origin rather than an internal WebUI.

This method is called from the main navigation policy decision in the same file:

```
- (void)webView:(WKWebView*)webView
    decidePolicyForNavigationAction:(WKNavigationAction*)action
                        preferences:(WKWebpagePreferences*)preferences
                      decisionHandler:
                          (void (^)(WKNavigationActionPolicy,
                                     WKWebpagePreferences*))handler {
  // ...
  GURL requestURL = net::GURLWithNSURL(action.request.URL);
  // ...
  ui::PageTransition transition =
      [self pageTransitionFromNavigationType:action.navigationType];
  if (isMainFrameNavigationAction) {
    web::NavigationContextImpl* context =
        [self contextForPendingMainFrameNavigationWithURL:requestURL];
    if (context &&
        (!context->IsRendererInitiated() ||
         (context->GetPageTransition() & ui::PAGE_TRANSITION_FORWARD_BACK))) {
      transition = context->GetPageTransition();
      if (context->IsLoadingErrorPage()) {
        decisionHandler(WKNavigationActionPolicyAllow);
        return;
      }
    }
  }
  // ...
  web::WebStatePolicyDecider::PolicyDecision policyDecision =
      web::WebStatePolicyDecider::PolicyDecision::Allow();
  if (web::GetWebClient()->IsAppSpecificURL(requestURL)) {
    if (![self shouldAllowAppSpecificURLNavigationAction:action
                                              transition:transition]) {
      policyDecision = web::WebStatePolicyDecider::PolicyDecision::Cancel();
    }
    if (policyDecision.ShouldAllowNavigation()) {
      [self.delegate navigationHandler:self createWebUIForURL:requestURL];
    }
  }
  // ...
}

```

The page transition value used here is derived from WebKit's navigation type and, for main-frame navigations with an associated `NavigationContext`, from the context's `GetPageTransition()`:

```
- (ui::PageTransition)pageTransitionFromNavigationType:
    (WKNavigationType)navigationType {
  switch (navigationType) {
    case WKNavigationTypeLinkActivated:
      return ui::PAGE_TRANSITION_LINK;
    case WKNavigationTypeFormSubmitted:
    case WKNavigationTypeFormResubmitted:
      return ui::PAGE_TRANSITION_FORM_SUBMIT;
    case WKNavigationTypeBackForward:
      return ui::PAGE_TRANSITION_FORWARD_BACK;
    case WKNavigationTypeReload:
      return ui::PAGE_TRANSITION_RELOAD;
    case WKNavigationTypeOther:
      // ... heuristic for "Other" ...
  }
}

```

Server-side redirects are handled in `didReceiveServerRedirectForProvisionalNavigation`:

```
- (void)webView:(WKWebView*)webView
    didReceiveServerRedirectForProvisionalNavigation:(WKNavigation*)navigation {
  // ...
  GURL webViewURL = net::GURLWithNSURL(webView.URL);
  web::NavigationContextImpl* context =
      [self.navigationStates contextForNavigation:navigation];
  if (!context) {
    return;
  }

  // Redirecting to a data url is always unsafe.
  if (webViewURL.SchemeIs(url::kDataScheme) ||
      // Block redirects to JavaScript schemes.
      webViewURL.SchemeIs(url::kJavaScriptScheme)) {
    self.pendingNavigationInfo.unsafeRedirect = YES;
  } else {
    context->SetUrl(webViewURL);
  }
  // ...
}

```

Redirects to `data:` and `javascript:` are treated as unsafe, but redirects to other schemes (including `chrome://`) simply update the context URL and do not change the page transition type.

Additionally, `NavigationManagerImpl::CreateNavigationItem` in `ios/web/navigation/navigation_manager_impl.mm` prevents certain internal rewrites from turning a reload of a non-app-specific URL into an app-specific load, but it does not apply to explicit server redirects that directly target an app-specific URL:

```
std::unique_ptr<NavigationItemImpl> NavigationManagerImpl::CreateNavigationItem(
    const GURL& url,
    const web::Referrer& referrer,
    ui::PageTransition transition,
    web::NavigationInitiationType initiation_type,
    web::HttpsUpgradeType https_upgrade_type,
    const GURL& previous_url,
    const std::vector<BrowserURLRewriter::URLRewriter>* additional_rewriters)
    const {
  GURL loaded_url(url);
  // ... URL rewriter logic ...

  // The URL should not be changed to app-specific URL if the load is
  // renderer-initiated or a reload requested by non-app-specific URL.
  if ((initiation_type == web::NavigationInitiationType::RENDERER_INITIATED ||
       PageTransitionCoreTypeIs(transition, ui::PAGE_TRANSITION_RELOAD)) &&
      loaded_url != url && web::GetWebClient()->IsAppSpecificURL(loaded_url) &&
      !web::GetWebClient()->IsAppSpecificURL(previous_url)) {
    loaded_url = url;
  }

  // ...
}

```

Putting these pieces together:

- A main-frame reload is represented as `PAGE_TRANSITION_RELOAD`, and this information is carried in the `NavigationContext`.
- A server redirect that happens during that reload does not change the transition type, but updates the URL to the redirect target.
- When the redirect target is an app-specific URL (for example `chrome://flags/`), `IsAppSpecificURL(requestURL)` is true and `shouldAllowAppSpecificURLNavigationAction` sees `PAGE_TRANSITION_RELOAD` and allows the navigation even if the last committed page was a regular HTTP(S) site.
- As a result, a regular web page can cause a navigation into a privileged internal `chrome://` WebUI page as long as the user has triggered a reload.

The provided proof-of-concept server in `web/reload_redirect/ios_nav_reload_test_server.py` demonstrates this behavior by:

- Serving a normal HTML page at `/ios-nav-reload-test` on first visit, and
- Issuing a `302` redirect to `chrome://flags/` on subsequent visits after setting a cookie to record that the client has already visited the page once.

When this server is accessed from iOS Chrome and the user manually reloads the test page, the browser successfully follows the redirect into `chrome://flags/`, confirming that a non-privileged origin can drive navigation into a privileged `chrome://` page via a reload-triggered server redirect.

#### Impact analysis

**Who can exploit it**

- Any remote web origin that a user visits in iOS Chrome, as long as the site can induce the user to reload the page once (for example via a UI hint).

**What they can do**

- After the user reloads the attacker-controlled page, the site can cause iOS Chrome to leave the attacker origin and open a privileged `chrome://` WebUI page such as `chrome://flags/` via a server-side redirect.
- This lets untrusted web content reliably drive navigation into internal configuration UIs that are normally intended to be reached only from trusted entry points (e.g. browser UI, bookmarks, or existing WebUI pages).

---

### The cause

#### What version of Chrome have you found the security issue in?

145.0.7632.1/stable

#### Is the security issue related to a crash?

No, it is not related to a crash.

#### Choose the type of vulnerability

Privilege Escalation

#### How would you like to be publicly acknowledged for your report?

Povcfe of Tencent Security Xuanwu Lab

## Attachments

- reload_redirect.mp4 (video/mp4, 9.7 MB)
- [reload_redirect.zip](attachments/reload_redirect.zip) (application/x-zip-compressed, 2.3 KB)

## Timeline

### po...@gmail.com (2026-01-19)

## patch

```
diff --git a/chromium/src/ios/web/navigation/crw_wk_navigation_handler.mm b/chromium/src/ios/web/navigation/crw_wk_navigation_handler.mm
--- a/chromium/src/ios/web/navigation/crw_wk_navigation_handler.mm
+++ b/chromium/src/ios/web/navigation/crw_wk_navigation_handler.mm
@@ -1370,9 +1370,9 @@
 // App specific pages have elevated privileges and WKWebView uses the same
 // renderer process for all page frames. With that Chromium does not allow
 // running App specific pages in the same process as a web site from the
 // internet. Allows navigation to app specific URL in the following cases:
 //   - last committed URL is app specific
-//   - navigation not a new navigation (back-forward or reload)
+//   - navigation not a new navigation (back-forward)
 //   - navigation is typed, generated or bookmark
 //   - navigation is performed in iframe and main frame is app-specific page
 - (BOOL)shouldAllowAppSpecificURLNavigationAction:(WKNavigationAction*)action
                                        transition:
                                            (ui::PageTransition)pageTransition {
@@ -1387,11 +1387,6 @@
   if (pageTransition & ui::PAGE_TRANSITION_FORWARD_BACK) {
     // Allow back-forward navigations.
     return YES;
   }
 
-  if (pageTransition & ui::PAGE_TRANSITION_RELOAD) {
-    // Allow reload navigations.
-    return YES;
-  }
-
   // Allow navigating to chrome:// pages if the navigation happens due to
   //  - user typing the url in the omnibox,
   //  - user tapping on a suggestion in the omnibox,

```

### dc...@chromium.org (2026-01-23)

Non-chrome pages should not be able to navigate to chrome URLs; I don't think this quite meets the criteria for high, but I think it's definitely at least medium. I tried to look around for other precedent, but wasn't really able to find much; if you're able to demonstrate that a navigation to chrome:// in iOS can have interesting/unfortunate side effects, I think that would probably be enough to raise this to High severity.

### ch...@google.com (2026-01-23)

Setting milestone because of s2 severity.

### ch...@google.com (2026-01-23)

Setting Priority to P1 to match Severity s2. If this is incorrect, please reset the priority. The automation bot account won't make this change again.

### dx...@google.com (2026-01-23)

Project: chromium/src  

Branch:  main  

Author:  Olivier Robin [olivierrobin@google.com](mailto:olivierrobin@google.com)  

Link:    <https://chromium-review.googlesource.com/7511016>

Prevent Reload navigations to app specific URLs

---


Expand for full commit details
```
     
    In conjunction with server redirection, reload allows any page to 
    navigate to chrome:// pages, which should be disallowed. 
     
    This fix was initially introduced to allow reloading from reader mode, 
    but is redundant with 
     crrev.com/c/7246254 so it is not needed anymore. 
     
    Fixed: 476898368 
    Change-Id: I5d33c0d6fe85ecf9fb67b78426ad7904fb03d074 
    Reviewed-on: https://chromium-review.googlesource.com/c/chromium/src/+/7511016 
    Auto-Submit: Olivier Robin <olivierrobin@chromium.org> 
    Commit-Queue: Mike Dougherty <michaeldo@chromium.org> 
    Reviewed-by: Mike Dougherty <michaeldo@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#1573932}

```

---

Files:

- M `ios/web/navigation/crw_wk_navigation_handler.mm`

---

Hash: [d2e7bad529aa30eab1a68da76ef9ab87ffafe132](https://chromiumdash.appspot.com/commit/d2e7bad529aa30eab1a68da76ef9ab87ffafe132)  

Date: Fri Jan 23 21:46:35 2026


---

### ch...@google.com (2026-01-24)

Security Merge Request Consideration: Requesting merge to beta (M145) because latest trunk commit (1573932) appears to be after beta branch point (1568190).
Security Merge Request: Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).

We have determined this fix is necessary on milestone(s): [].

Please answer the following questions so that we can safely process this merge request:

1. Which CLs should be backmerged? (Please include Gerrit links.)
2. Has this fix been verified on Canary to not pose any stability regressions?
3. Does this fix pose any potential non-verifiable stability risks?
4. Does this fix pose any known compatibility risks?
5. Does it require manual verification by the test team? If so, please describe required testing.
6. (no answer required) Please check the OS custom field to ensure all impacted OSes are checked!

### ch...@google.com (2026-01-24)

Merge review required: M145 is already shipping to beta.

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

### dr...@chromium.org (2026-01-28)

We still need to update our automation, but we are no longer merging S2s. Updating labels.

### sp...@google.com (2026-02-20)

** NOTE: This is an automatically generated email **

Hello,

Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $1000.00 for this report.

Rationale for this decision:
Baseline // Lower Impact Exploitation mitigation bypass


Important: This payment will be issued by Bugcrowd. You will receive an email from Bugcrowd in the next 24 hours which contains a submission you must claim to be rewarded.

If you do not receive an email from them, please check your spam folder and then reach out to us via a comment here. For issues related to Bugcrowd itself, please contact them via https://bugcrowd.com/support.


Thank you for your efforts and helping us make Chrome more secure for all users!

Cheers,
Chrome VRP Panel Bot


P.S. One other thing we'd like to mention:

* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.

Please contact security-vrp@chromium.org with any questions.

### ch...@google.com (2026-05-02)

This bug has been closed for more than 14 weeks. Removing issue access restrictions.

## Bounty Award

> Baseline // Lower Impact Exploitation mitigation bypass

---
*Data from [Chromium Issue Tracker](https://issues.chromium.org/issues/476898368)*
