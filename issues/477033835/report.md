# PDFium  heap-buffer-overflow at opj_j2k_read_sod

| Field | Value |
|-------|-------|
| **Issue ID** | [477033835](https://issues.chromium.org/issues/477033835) |
| **Status** | Assigned |
| **Severity** | S3-Low |
| **Priority** | P1 |
| **Component** | PDFium |
| **Platforms** | Linux, Mac, Windows, ChromeOS |
| **Reporter** | ke...@gmail.com |
| **Assignee** | ts...@chromium.org |
| **Created** | 2026-01-19 |
| **Bounty** | $11,000.00 |

## Description

VULNERABILITY DETAILS

A heap buffer overflow vulnerability exists in OpenJPEG's TLM (Tile Length Marker) decoding functionality. The vulnerability allows an attacker to write out-of-bounds to heap memory when processing a specially crafted JPEG 2000 file. The root cause is a missing bounds check in `opj_j2k_read_sod()` where the `current_tpsno` (current tile-part number) value derived from SOT markers is used to index the `tp_index` array without validating it against the allocated size (`nb_tps`).

REPRODUCTION CASE

Attached testcase uses multiple tiles, and more SOT fields, to crash even without ASAN. Pdfium\_test ASAN log:

```
==48964==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x1235a21aa800 at pc 0x7ff74b7de0a0 bp 0x0057daefe200 sp 0x0057daefe248
WRITE of size 8 at 0x1235a21aa800 thread T0
    #0 0x7ff74b7de09f in opj_j2k_read_sod C:\b\s\w\ir\cache\builder\src\third_party\pdfium\third_party\libopenjpeg\j2k.c:5086
    #1 0x7ff74b7de09f in opj_j2k_read_tile_header C:\b\s\w\ir\cache\builder\src\third_party\pdfium\third_party\libopenjpeg\j2k.c:9923:19
    #2 0x7ff74b7f61f7 in opj_j2k_decode_tiles C:\b\s\w\ir\cache\builder\src\third_party\pdfium\third_party\libopenjpeg\j2k.c:12108:19
    #3 0x7ff74b7e4d56 in opj_j2k_exec C:\b\s\w\ir\cache\builder\src\third_party\pdfium\third_party\libopenjpeg\j2k.c:9190
    #4 0x7ff74b7e4d56 in opj_j2k_decode C:\b\s\w\ir\cache\builder\src\third_party\pdfium\third_party\libopenjpeg\j2k.c:12455:11
    #5 0x7ff74b70f36e in fxcodec::CJPX_Decoder::StartDecode(void) C:\b\s\w\ir\cache\builder\src\third_party\pdfium\core\fxcodec\jpx\cjpx_decoder.cpp:519:11
    #6 0x7ff74b934e72 in CPDF_DIB::LoadJpxBitmap(unsigned char) C:\b\s\w\ir\cache\builder\src\third_party\pdfium\core\fpdfapi\page\cpdf_dib.cpp:597:17
    #7 0x7ff74b92e7e2 in CPDF_DIB::CreateDecoder(unsigned char) C:\b\s\w\ir\cache\builder\src\third_party\pdfium\core\fpdfapi\page\cpdf_dib.cpp:452:22
    #8 0x7ff74b9310f6 in CPDF_DIB::StartLoadDIBBase(bool, class CPDF_Dictionary const *, class CPDF_Dictionary const *, bool, enum CPDF_ColorSpace::Family, bool, class CFX_STemplate<int> const &) C:\b\s\w\ir\cache\builder\src\third_party\pdfium\core\fpdfapi\page\cpdf_dib.cpp:207:31
    #9 0x7ff74b966e48 in CPDF_PageImageCache::Entry::StartGetCachedBitmap(class CPDF_PageImageCache *, class CPDF_Dictionary const *, class CPDF_Dictionary const *, bool, enum CPDF_ColorSpace::Family, bool, class CFX_STemplate<int> const &) C:\b\s\w\ir\cache\builder\src\third_party\pdfium\core\fpdfapi\page\cpdf_pageimagecache.cpp:283:60
    #10 0x7ff74b966690 in CPDF_PageImageCache::StartGetCachedBitmap(class fxcrt::RetainPtr<class CPDF_Image>, class CPDF_Dictionary const *, class CPDF_Dictionary const *, bool, enum CPDF_ColorSpace::Family, bool, class CFX_STemplate<int> const &) C:\b\s\w\ir\cache\builder\src\third_party\pdfium\core\fpdfapi\page\cpdf_pageimagecache.cpp:191:53
    #11 0x7ff74b9574f8 in CPDF_ImageLoader::Start(class CPDF_ImageObject const *, class CPDF_PageImageCache *, class CPDF_Dictionary const *, class CPDF_Dictionary const *, bool, enum CPDF_ColorSpace::Family, bool, class CFX_STemplate<int> const &) C:\b\s\w\ir\cache\builder\src\third_party\pdfium\core\fpdfapi\page\cpdf_imageloader.cpp:35:31
    #12 0x7ff74b9b270e in CPDF_ImageRenderer::StartLoadDIBBase(void) C:\b\s\w\ir\cache\builder\src\third_party\pdfium\core\fpdfapi\render\cpdf_imagerenderer.cpp:73:17
    #13 0x7ff74b9b77d0 in CPDF_ImageRenderer::Start(class CPDF_ImageObject *, class CFX_Matrix const &, bool) C:\b\s\w\ir\cache\builder\src\third_party\pdfium\core\fpdfapi\render\cpdf_imagerenderer.cpp:202:7
    #14 0x7ff74b9d09d1 in CPDF_RenderStatus::ContinueSingleObject(class CPDF_PageObject *, class CFX_Matrix const &, class PauseIndicatorIface *) C:\b\s\w\ir\cache\builder\src\third_party\pdfium\core\fpdfapi\render\cpdf_renderstatus.cpp:286:25
    #15 0x7ff74b9bc09a in CPDF_ProgressiveRenderer::Continue(class PauseIndicatorIface *) C:\b\s\w\ir\cache\builder\src\third_party\pdfium\core\fpdfapi\render\cpdf_progressiverenderer.cpp:95:29
    #16 0x7ff74ad0ae5c in `anonymous namespace'::RenderPageImpl C:\b\s\w\ir\cache\builder\src\third_party\pdfium\fpdfsdk\cpdfsdk_renderpage.cpp:87:23
    #17 0x7ff74ad0b22d in CPDFSDK_RenderPageWithContext(class CPDF_PageRenderContext *, class CPDF_Page *, int, int, int, int, int, int, struct FPDF_COLORSCHEME_ const *, bool, class CPDFSDK_PauseAdapter *) C:\b\s\w\ir\cache\builder\src\third_party\pdfium\fpdfsdk\cpdfsdk_renderpage.cpp:117:3
    #18 0x7ff74ad23008 in FPDF_RenderPageBitmapWithColorScheme_Start C:\b\s\w\ir\cache\builder\src\third_party\pdfium\fpdfsdk\fpdf_progressive.cpp:83:3
    #19 0x7ff74acae42a in `anonymous namespace'::ProgressiveBitmapPageRenderer::Start C:\b\s\w\ir\cache\builder\src\third_party\pdfium\testing\pdfium_test.cc:1137:9
    #20 0x7ff74aca5254 in `anonymous namespace'::PdfProcessor::ProcessPage C:\b\s\w\ir\cache\builder\src\third_party\pdfium\testing\pdfium_test.cc:1607
    #21 0x7ff74aca5254 in `anonymous namespace'::Processor::ProcessPdf C:\b\s\w\ir\cache\builder\src\third_party\pdfium\testing\pdfium_test.cc:1789
    #22 0x7ff74aca5254 in main C:\b\s\w\ir\cache\builder\src\third_party\pdfium\testing\pdfium_test.cc:2117:17
    #23 0x7ff750dcb22f in invoke_main D:\a\_work\1\s\src\vctools\crt\vcstartup\src\startup\exe_common.inl:78
    #24 0x7ff750dcb22f in __scrt_common_main_seh D:\a\_work\1\s\src\vctools\crt\vcstartup\src\startup\exe_common.inl:288
    #25 0x7ff99d2ce8d6  (C:\WINDOWS\System32\KERNEL32.DLL+0x18002e8d6)
    #26 0x7ff99dd6c53b  (C:\WINDOWS\SYSTEM32\ntdll.dll+0x18008c53b)

0x1235a21aa800 is located 8 bytes after 24-byte region [0x1235a21aa7e0,0x1235a21aa7f8)
allocated by thread T0 here:
    #0 0x7ff8e583ca26  (F:\fuzz\chromium-146.0.7637.0-win64-asan\clang_rt.asan_dynamic-x86_64.dll+0x18004ca26)
    #1 0x7ff7509f494d in calloc C:\b\s\w\ir\cache\builder\src\third_party\llvm\compiler-rt\lib\asan\asan_malloc_win_thunk.cpp:82
    #2 0x7ff74b7e9a35 in opj_j2k_build_tp_index_from_tlm C:\b\s\w\ir\cache\builder\src\third_party\pdfium\third_party\libopenjpeg\j2k.c:8948:57
    #3 0x7ff74b7e7b33 in opj_j2k_read_header_procedure C:\b\s\w\ir\cache\builder\src\third_party\pdfium\third_party\libopenjpeg\j2k.c:9161:5
    #4 0x7ff74b7da366 in opj_j2k_exec C:\b\s\w\ir\cache\builder\src\third_party\pdfium\third_party\libopenjpeg\j2k.c:9190
    #5 0x7ff74b7da366 in opj_j2k_read_header C:\b\s\w\ir\cache\builder\src\third_party\pdfium\third_party\libopenjpeg\j2k.c:8535:11
    #6 0x7ff74b70c620 in fxcodec::CJPX_Decoder::Init(class pdfium::span<unsigned char const, -1, unsigned char const *>, unsigned char, bool) C:\b\s\w\ir\cache\builder\src\third_party\pdfium\core\fxcodec\jpx\cjpx_decoder.cpp:503:8
    #7 0x7ff74b70c002 in fxcodec::CJPX_Decoder::Create(class pdfium::span<unsigned char const, -1, unsigned char const *>, enum fxcodec::CJPX_Decoder::ColorSpaceOption, unsigned char, bool) C:\b\s\w\ir\cache\builder\src\third_party\pdfium\core\fxcodec\jpx\cjpx_decoder.cpp:438:17
    #8 0x7ff74b934e1b in CPDF_DIB::LoadJpxBitmap(unsigned char) C:\b\s\w\ir\cache\builder\src\third_party\pdfium\core\fpdfapi\page\cpdf_dib.cpp:587:7
    #9 0x7ff74b92e7e2 in CPDF_DIB::CreateDecoder(unsigned char) C:\b\s\w\ir\cache\builder\src\third_party\pdfium\core\fpdfapi\page\cpdf_dib.cpp:452:22
    #10 0x7ff74b9310f6 in CPDF_DIB::StartLoadDIBBase(bool, class CPDF_Dictionary const *, class CPDF_Dictionary const *, bool, enum CPDF_ColorSpace::Family, bool, class CFX_STemplate<int> const &) C:\b\s\w\ir\cache\builder\src\third_party\pdfium\core\fpdfapi\page\cpdf_dib.cpp:207:31
    #11 0x7ff74b966e48 in CPDF_PageImageCache::Entry::StartGetCachedBitmap(class CPDF_PageImageCache *, class CPDF_Dictionary const *, class CPDF_Dictionary const *, bool, enum CPDF_ColorSpace::Family, bool, class CFX_STemplate<int> const &) C:\b\s\w\ir\cache\builder\src\third_party\pdfium\core\fpdfapi\page\cpdf_pageimagecache.cpp:283:60
    #12 0x7ff74b966690 in CPDF_PageImageCache::StartGetCachedBitmap(class fxcrt::RetainPtr<class CPDF_Image>, class CPDF_Dictionary const *, class CPDF_Dictionary const *, bool, enum CPDF_ColorSpace::Family, bool, class CFX_STemplate<int> const &) C:\b\s\w\ir\cache\builder\src\third_party\pdfium\core\fpdfapi\page\cpdf_pageimagecache.cpp:191:53
    #13 0x7ff74b9574f8 in CPDF_ImageLoader::Start(class CPDF_ImageObject const *, class CPDF_PageImageCache *, class CPDF_Dictionary const *, class CPDF_Dictionary const *, bool, enum CPDF_ColorSpace::Family, bool, class CFX_STemplate<int> const &) C:\b\s\w\ir\cache\builder\src\third_party\pdfium\core\fpdfapi\page\cpdf_imageloader.cpp:35:31
    #14 0x7ff74b9b270e in CPDF_ImageRenderer::StartLoadDIBBase(void) C:\b\s\w\ir\cache\builder\src\third_party\pdfium\core\fpdfapi\render\cpdf_imagerenderer.cpp:73:17
    #15 0x7ff74b9b77d0 in CPDF_ImageRenderer::Start(class CPDF_ImageObject *, class CFX_Matrix const &, bool) C:\b\s\w\ir\cache\builder\src\third_party\pdfium\core\fpdfapi\render\cpdf_imagerenderer.cpp:202:7
    #16 0x7ff74b9d09d1 in CPDF_RenderStatus::ContinueSingleObject(class CPDF_PageObject *, class CFX_Matrix const &, class PauseIndicatorIface *) C:\b\s\w\ir\cache\builder\src\third_party\pdfium\core\fpdfapi\render\cpdf_renderstatus.cpp:286:25
    #17 0x7ff74b9bc09a in CPDF_ProgressiveRenderer::Continue(class PauseIndicatorIface *) C:\b\s\w\ir\cache\builder\src\third_party\pdfium\core\fpdfapi\render\cpdf_progressiverenderer.cpp:95:29
    #18 0x7ff74ad0ae5c in `anonymous namespace'::RenderPageImpl C:\b\s\w\ir\cache\builder\src\third_party\pdfium\fpdfsdk\cpdfsdk_renderpage.cpp:87:23
    #19 0x7ff74ad0b22d in CPDFSDK_RenderPageWithContext(class CPDF_PageRenderContext *, class CPDF_Page *, int, int, int, int, int, int, struct FPDF_COLORSCHEME_ const *, bool, class CPDFSDK_PauseAdapter *) C:\b\s\w\ir\cache\builder\src\third_party\pdfium\fpdfsdk\cpdfsdk_renderpage.cpp:117:3
    #20 0x7ff74ad23008 in FPDF_RenderPageBitmapWithColorScheme_Start C:\b\s\w\ir\cache\builder\src\third_party\pdfium\fpdfsdk\fpdf_progressive.cpp:83:3
    #21 0x7ff74acae42a in `anonymous namespace'::ProgressiveBitmapPageRenderer::Start C:\b\s\w\ir\cache\builder\src\third_party\pdfium\testing\pdfium_test.cc:1137:9
    #22 0x7ff74aca5254 in `anonymous namespace'::PdfProcessor::ProcessPage C:\b\s\w\ir\cache\builder\src\third_party\pdfium\testing\pdfium_test.cc:1607
    #23 0x7ff74aca5254 in `anonymous namespace'::Processor::ProcessPdf C:\b\s\w\ir\cache\builder\src\third_party\pdfium\testing\pdfium_test.cc:1789
    #24 0x7ff74aca5254 in main C:\b\s\w\ir\cache\builder\src\third_party\pdfium\testing\pdfium_test.cc:2117:17
    #25 0x7ff750dcb22f in invoke_main D:\a\_work\1\s\src\vctools\crt\vcstartup\src\startup\exe_common.inl:78
    #26 0x7ff750dcb22f in __scrt_common_main_seh D:\a\_work\1\s\src\vctools\crt\vcstartup\src\startup\exe_common.inl:288
    #27 0x7ff99d2ce8d6  (C:\WINDOWS\System32\KERNEL32.DLL+0x18002e8d6)
    #28 0x7ff99dd6c53b  (C:\WINDOWS\SYSTEM32\ntdll.dll+0x18008c53b)

SUMMARY: AddressSanitizer: heap-buffer-overflow C:\b\s\w\ir\cache\builder\src\third_party\pdfium\third_party\libopenjpeg\j2k.c:5086 in opj_j2k_read_sod
Shadow bytes around the buggy address:
  0x1235a21aa580: fd fd fa fa fd fd fd fd fa fa fd fd fd fd fa fa
  0x1235a21aa600: fd fd fd fd fa fa 00 00 00 00 fa fa 00 00 00 00
  0x1235a21aa680: fa fa fd fd fd fd fa fa fd fd fd fd fa fa fd fd
  0x1235a21aa700: fd fd fa fa 00 00 00 00 fa fa fd fd fd fa fa fa
  0x1235a21aa780: 00 00 00 00 fa fa 00 00 00 fa fa fa 00 00 00 fa
=>0x1235a21aa800:[fa]fa 00 00 00 fa fa fa fa fa fa fa fa fa fa fa
  0x1235a21aa880: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x1235a21aa900: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x1235a21aa980: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x1235a21aaa00: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x1235a21aaa80: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
Shadow byte legend (one shadow byte represents 8 application bytes):
  Addressable:           00
  Partially addressable: 01 02 03 04 05 06 07
  Heap left redzone:       fa
  Freed heap region:       fd
  Stack left redzone:      f1
  Stack mid redzone:       f2
  Stack right redzone:     f3
  Stack after return:      f5
  Stack use after scope:   f8
  Global redzone:          f9
  Global init order:       f6
  Poisoned by user:        f7
  Container overflow:      fc
  Array cookie:            ac
  Intra object redzone:    bb
  ASan internal:           fe
  Left alloca redzone:     ca
  Right alloca redzone:    cb

```
## Root Cause Analysis

### Overview

The vulnerability stems from a mismatch between:

1. The `tp_index` array size, which is allocated based on TLM (Tile Length Marker) entries
2. The `current_tpsno` value, which is set from SOT (Start Of Tile-part) marker's `TPsot` field

When a maliciously crafted file provides inconsistent TLM and SOT data, the decoder can write beyond the allocated `tp_index` buffer.

#### Step 1: TLM Allocates tp\_index Based on Tile-Part Count

In j2k.c `opj_j2k_build_tp_index_from_tlm()` (lines 8914-8946), the `tp_index` array is allocated based on the number of tile-part entries found in TLM markers:

```
// Lines 8914-8919: First pass counts tile-parts per tile
for (i = 0; i < l_tlm->m_entries_count; ++i) {
    OPJ_UINT32 l_tile_index_no = l_tlm->m_tile_part_infos[i].m_tile_index;
    assert(l_tile_index_no < p_j2k->cstr_index->nb_of_tiles);
    p_j2k->cstr_index->tile_index[l_tile_index_no].tileno = l_tile_index_no;
    ++p_j2k->cstr_index->tile_index[l_tile_index_no].current_nb_tps;
}

// Lines 8938-8946: Allocate tp_index based on count
if (!l_tile_index->tp_index) {
    l_tile_index->tp_index = (opj_tp_index_t *) opj_calloc(
                                 l_tile_index->current_nb_tps, sizeof(opj_tp_index_t));
    if (! l_tile_index->tp_index) {
        opj_event_msg(p_manager, EVT_ERROR,
                      "opj_j2k_build_tp_index_from_tlm(): tile index allocation failed\n");
        goto error;
    }
}

```

If TLM says tile 0 has 2 tile-parts, then `tp_index[2]` is allocated with valid indices 0 and 1.

#### Step 2: SOT Sets current\_tpsno Without Sufficient Validation

In `opj_j2k_read_sot()` (lines 4659-4660), the `current_tpsno` is set directly from the SOT marker's `TPsot` field:

```
// Lines 4659-4660: current_tpsno set UNCONDITIONALLY from SOT
p_j2k->cstr_index->tile_index[p_j2k->m_current_tile_number].current_tpsno =
    l_current_part;

```
#### Step 3: Inadequate TLM Invalidation Check

The check that should invalidate TLM when SOT data conflicts (lines 4662-4668) only compares `TNsot` (total number of tile-parts) against TLM data, NOT `TPsot` (current tile-part number):

```
// Lines 4662-4668: Only checks TNsot, NOT TPsot
if (!p_j2k->m_specific_param.m_decoder.m_tlm.m_is_invalid &&
        l_num_parts >   // ← l_num_parts is TNsot
        p_j2k->cstr_index->tile_index[p_j2k->m_current_tile_number].nb_tps) {
    opj_event_msg(p_manager, EVT_WARNING,
                  "SOT marker for tile %u declares more tile-parts than found in TLM marker.",
                  p_j2k->m_current_tile_number);
    p_j2k->m_specific_param.m_decoder.m_tlm.m_is_invalid = OPJ_TRUE;
}

```

When `TNsot = 0` (unknown), this check passes even if `TPsot >= nb_tps`.

#### Step 4: Vulnerable Access in opj\_j2k\_read\_sod

In `opj_j2k_read_sod()` (lines 5083-5090), the `current_tpsno` value is used to index `tp_index` **without any bounds check**:

```
// Lines 5083-5090: VULNERABLE - No bounds check before array access
OPJ_UINT32 l_current_tile_part =
    l_cstr_index->tile_index[p_j2k->m_current_tile_number].current_tpsno;
l_cstr_index->tile_index[p_j2k->m_current_tile_number].tp_index[l_current_tile_part].end_header
    =
        l_current_pos;
l_cstr_index->tile_index[p_j2k->m_current_tile_number].tp_index[l_current_tile_part].end_pos
    =
        l_current_pos + p_j2k->m_specific_param.m_decoder.m_sot_length + 2;

```

Compare this to the protected code in `opj_j2k_add_tlmarker()` (lines 8462-8465):

```
// Lines 8462-8465: PROTECTED - Has bounds check
if (cstr_index->tile_index[tileno].tp_index &&
        l_current_tile_part < cstr_index->tile_index[tileno].nb_tps) {  // ← Bounds check
    cstr_index->tile_index[tileno].tp_index[l_current_tile_part].start_pos = pos;
}

```
### Memory Corruption Details

The overflow writes `OPJ_OFF_T` values to heap memory:

```
typedef struct opj_tp_index {
    OPJ_OFF_T start_pos;    // 8 bytes
    OPJ_OFF_T end_header;   // 8 bytes - WRITTEN BY VULNERABLE CODE
    OPJ_OFF_T end_pos;      // 8 bytes - WRITTEN BY VULNERABLE CODE
} opj_tp_index_t;           // Total: 24 bytes per entry

```

**Attacker-controlled values:**

- `end_header` = current stream position (partially controlled via file layout)
- `end_pos` = current stream position + SOT length (attacker-controlled)

### Fix : Add Bounds Check in opj\_j2k\_read\_sod

```
diff --git a/src/lib/openjp2/j2k.c b/src/lib/openjp2/j2k.c
index a2014c8..c4304c7 100644
--- a/src/lib/openjp2/j2k.c
+++ b/src/lib/openjp2/j2k.c
@@ -5082,12 +5082,15 @@ static OPJ_BOOL opj_j2k_read_sod(opj_j2k_t *p_j2k,

         OPJ_UINT32 l_current_tile_part =
             l_cstr_index->tile_index[p_j2k->m_current_tile_number].current_tpsno;
+        if (l_cstr_index->tile_index[p_j2k->m_current_tile_number].tp_index &&
+            l_current_tile_part < l_cstr_index->tile_index[p_j2k->m_current_tile_number].nb_tps) {
         l_cstr_index->tile_index[p_j2k->m_current_tile_number].tp_index[l_current_tile_part].end_header
             =
                 l_current_pos;
         l_cstr_index->tile_index[p_j2k->m_current_tile_number].tp_index[l_current_tile_part].end_pos
             =
                 l_current_pos + p_j2k->m_specific_param.m_decoder.m_sot_length + 2;
+            }

         if (OPJ_FALSE == opj_j2k_add_tlmarker(p_j2k->m_current_tile_number,
                                               l_cstr_index,

```

CREDIT INFORMATION

Reporter credit: soiax

## Attachments

- [test2n.j2k.pdf](attachments/test2n.j2k.pdf) (application/pdf, 1.1 KB)

## Timeline

### ke...@gmail.com (2026-01-19)

Bisects to Update OpenJPEG to 2.5.3: <https://pdfium.googlesource.com/pdfium/+/a4cbdc9ed1d06a16bae780f8e25ab6b385bc0468>

I haven't reported it to Openjpeg, should i wait with that, or i can report it now?

### dc...@chromium.org (2026-01-20)

Reporter, can you file a security bug with upstream? Once it's fixed upstream, we'll roll the fix into pdfium.

### ke...@gmail.com (2026-01-20)

Filed at <https://github.com/uclouvain/openjpeg/issues/1620>

### ch...@google.com (2026-01-21)

Setting Priority to P1 to match Severity s1. If this is incorrect, please reset the priority. The automation bot account won't make this change again.

### ch...@google.com (2026-02-04)

tsepez: Uh oh! This issue still open and hasn't been updated in the last 14 days. This is a serious vulnerability, and we want to ensure that there's progress. Could you please leave an update with the current status and any potential blockers?

If you're not the right owner for this issue, could you please remove yourself as soon as possible or help us find the right one?

If the issue is fixed or you can't reproduce it, please close the bug. If you've started working on a fix, please set the status to Started.[internal debugging info: security\_nag\_check]

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.

### ts...@google.com (2026-02-04)

External dependency. No action upstream.  May need to patch locally.

### ts...@google.com (2026-02-04)

https://pdfium-review.googlesource.com/c/pdfium/+/142390 patches this locally, using the suggested fix which is similar to what is done elsewhere in the file.

### dx...@google.com (2026-02-04)

Project: pdfium  

Branch:  main  

Author:  Tom Sepez [tsepez@google.com](mailto:tsepez@google.com)  

Link:    <https://pdfium-review.googlesource.com/142390>

Fix indexing in opj\_j2k\_read\_sod()

---


Expand for full commit details
```
     
    Apply same check as in opj_j2k_add_tlmarker(). 
     
    Bug: 477033835 
    Change-Id: I18def8cdd683cb1e8ed9359914e286de9837d382 
    Reviewed-on: https://pdfium-review.googlesource.com/c/pdfium/+/142390 
    Auto-Submit: Tom Sepez <tsepez@chromium.org> 
    Reviewed-by: Lei Zhang <thestig@chromium.org> 
    Commit-Queue: Lei Zhang <thestig@chromium.org> 
    Commit-Queue: Tom Sepez <tsepez@chromium.org>

```

---

Files:

- A `third_party/libopenjpeg/0047-opj_j2k_read_sod.patch`
- M `third_party/libopenjpeg/README.pdfium`
- M `third_party/libopenjpeg/j2k.c`

---

Hash: 40e5a93503adcdd4b9b3fdc085a31a58b7b0f2dd  

Date: Wed Feb 4 18:59:25 2026


---

### ch...@google.com (2026-02-04)

Dear owner, thanks for fixing this bug. We've reopened it because:

- Security bugs need the Severity (S0-S3) and the Found In set, which will enable the bots to request merges to the correct branches (as well as helping out our vulnerability reward and CVE processes). Please consult with any Chrome security contact ([security@chromium.org](mailto:security@chromium.org)) to arrange to set these labels. Severity guidelines: <https://chromium.googlesource.com/chromium/src/+/refs/heads/main/docs/security/severity-guidelines.md#severity-guidelines-for-security-issues> FoundIn guidelines: <https://chromium.googlesource.com/chromium/src/+/main/docs/security/security-labels.md#labels-relevant-for-any-type_bug_security>
  After resolving the above issue(s), this bug can be marked closed again. Thanks for your time!

### dx...@google.com (2026-02-05)

Project: chromium/src  

Branch:  main  

Author:  chromium-autoroll [chromium-autoroll@skia-public.iam.gserviceaccount.com](mailto:chromium-autoroll@skia-public.iam.gserviceaccount.com)  

Link:    <https://chromium-review.googlesource.com/7547281>

Manual roll PDFium from 051cbf295d73 to b4361c5b1c71 (2 revisions)

---


Expand for full commit details
```
     
    Manual roll requested by thestig@google.com 
     
    https://pdfium.googlesource.com/pdfium.git/+log/051cbf295d73..b4361c5b1c71 
     
    2026-02-04 thestig@chromium.org Clean up EnumGdiFonts() parameters 
    2026-02-04 tsepez@google.com Fix indexing in opj_j2k_read_sod() 
     
    If this roll has caused a breakage, revert this CL and stop the roller 
    using the controls here: 
    https://autoroll.skia.org/r/pdfium-autoroll 
    Please CC dhoss@chromium.org,thestig@chromium.org,thestig@google.com on the revert to ensure that a human 
    is aware of the problem. 
     
    To file a bug in PDFium: https://bugs.chromium.org/p/pdfium/issues/entry 
    To file a bug in Chromium: https://bugs.chromium.org/p/chromium/issues/entry 
     
    To report a problem with the AutoRoller itself, please file a bug: 
    https://issues.skia.org/issues/new?component=1389291&template=1850622 
     
    Documentation for the AutoRoller is here: 
    https://skia.googlesource.com/buildbot/+doc/main/autoroll/README.md 
     
    Bug: chromium:477033835 
    Tbr: thestig@google.com 
    Change-Id: I86be5b2c201276f3a2fba3a0a0f13e7f477c4c14 
    Reviewed-on: https://chromium-review.googlesource.com/c/chromium/src/+/7547281 
    Commit-Queue: chromium-autoroll <chromium-autoroll@skia-public.iam.gserviceaccount.com> 
    Bot-Commit: chromium-autoroll <chromium-autoroll@skia-public.iam.gserviceaccount.com> 
    Cr-Commit-Position: refs/heads/main@{#1579859}

```

---

Files:

- M `DEPS`
- M `third_party/pdfium`

---

Hash: [891dabbf2a4c0502dc570c2793b1d060dfe9b059](https://chromiumdash.appspot.com/commit/891dabbf2a4c0502dc570c2793b1d060dfe9b059)  

Date: Thu Feb 5 03:31:46 2026


---

### ch...@google.com (2026-02-05)

Security Merge Request Consideration: Requesting merge to stable (M144) because latest trunk commit (1579859) appears to be after stable branch point (1552494).
Security Merge Request Consideration: Requesting merge to beta (M145) because latest trunk commit (1579859) appears to be after beta branch point (1568190).
Security Merge Request - Manual Review: Merge review required: a commit with DEPS changes was detected.

Security Merge Request - Manual Review: Merge review required: a commit with DEPS changes was detected.

Security Merge Request: Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).

We have determined this fix is necessary on milestone(s): [144, 145].

Please answer the following questions so that we can safely process this merge request:

1. Which CLs should be backmerged? (Please include Gerrit links.)
2. Has this fix been verified on Canary to not pose any stability regressions?
3. Does this fix pose any potential non-verifiable stability risks?
4. Does this fix pose any known compatibility risks?
5. Does it require manual verification by the test team? If so, please describe required testing.
6. (no answer required) Please check the OS custom field to ensure all impacted OSes are checked!

### ke...@gmail.com (2026-02-05)

I would like to donate any reward to charity.

Minor nit: in README.pdfium, “Fix out of bounds read” should be “write”, since this is an out-of-bounds write.

### dr...@chromium.org (2026-02-09)

Canary stability looks good. Approving merge to M144 and M145.

### dx...@google.com (2026-02-10)

Project: pdfium  

Branch:  chromium/7362  

Author:  Tom Sepez [tsepez@google.com](mailto:tsepez@google.com)  

Link:    <https://pdfium-review.googlesource.com/142592>

[M145] Fix indexing in opj\_j2k\_read\_sod()

---


Expand for full commit details
```
     
    Apply same check as in opj_j2k_add_tlmarker(). 
     
    Bug: 477033835 
    Change-Id: I18def8cdd683cb1e8ed9359914e286de9837d382 
    Reviewed-on: https://pdfium-review.googlesource.com/c/pdfium/+/142390 
    Auto-Submit: Tom Sepez <tsepez@chromium.org> 
    Reviewed-by: Lei Zhang <thestig@chromium.org> 
    Commit-Queue: Lei Zhang <thestig@chromium.org> 
    Commit-Queue: Tom Sepez <tsepez@chromium.org> 
    (cherry picked from commit 40e5a93503adcdd4b9b3fdc085a31a58b7b0f2dd) 
    Reviewed-on: https://pdfium-review.googlesource.com/c/pdfium/+/142592

```

---

Files:

- A `third_party/libopenjpeg/0047-opj_j2k_read_sod.patch`
- M `third_party/libopenjpeg/README.pdfium`
- M `third_party/libopenjpeg/j2k.c`

---

Hash: 80060281445bf24bc734d26bee96aa77cf072219  

Date: Tue Feb 10 00:37:21 2026


---

### dx...@google.com (2026-02-10)

Project: pdfium  

Branch:  chromium/7559  

Author:  Tom Sepez [tsepez@google.com](mailto:tsepez@google.com)  

Link:    <https://pdfium-review.googlesource.com/142593>

[M144] Fix indexing in opj\_j2k\_read\_sod()

---


Expand for full commit details
```
     
    Apply same check as in opj_j2k_add_tlmarker(). 
     
    Bug: 477033835 
    Change-Id: I18def8cdd683cb1e8ed9359914e286de9837d382 
    Reviewed-on: https://pdfium-review.googlesource.com/c/pdfium/+/142390 
    Auto-Submit: Tom Sepez <tsepez@chromium.org> 
    Reviewed-by: Lei Zhang <thestig@chromium.org> 
    Commit-Queue: Lei Zhang <thestig@chromium.org> 
    Commit-Queue: Tom Sepez <tsepez@chromium.org> 
    (cherry picked from commit 40e5a93503adcdd4b9b3fdc085a31a58b7b0f2dd) 
    Reviewed-on: https://pdfium-review.googlesource.com/c/pdfium/+/142593

```

---

Files:

- A `third_party/libopenjpeg/0047-opj_j2k_read_sod.patch`
- M `third_party/libopenjpeg/README.pdfium`
- M `third_party/libopenjpeg/j2k.c`

---

Hash: 53909bbc260e7bc9fe54f2e77bb0ad653dc345fe  

Date: Tue Feb 10 00:37:53 2026


---

### dx...@google.com (2026-02-10)

Project: pdfium  

Branch:  chromium/7632  

Author:  Tom Sepez [tsepez@google.com](mailto:tsepez@google.com)  

Link:    <https://pdfium-review.googlesource.com/142630>

[M145] Redo: Fix indexing in opj\_j2k\_read\_sod()

---


Expand for full commit details
```
     
    Supply correct branch number this time. 
     
    Apply same check as in opj_j2k_add_tlmarker(). 
     
    Bug: 477033835 
    Change-Id: I18def8cdd683cb1e8ed9359914e286de9837d382 
    Reviewed-on: https://pdfium-review.googlesource.com/c/pdfium/+/142390 
    Auto-Submit: Tom Sepez <tsepez@chromium.org> 
    Reviewed-by: Lei Zhang <thestig@chromium.org> 
    Commit-Queue: Lei Zhang <thestig@chromium.org> 
    Commit-Queue: Tom Sepez <tsepez@chromium.org> 
    (cherry picked from commit 40e5a93503adcdd4b9b3fdc085a31a58b7b0f2dd) 
    Reviewed-on: https://pdfium-review.googlesource.com/c/pdfium/+/142630 
    Reviewed-by: Tom Sepez <tsepez@chromium.org>

```

---

Files:

- A `third_party/libopenjpeg/0047-opj_j2k_read_sod.patch`
- M `third_party/libopenjpeg/README.pdfium`
- M `third_party/libopenjpeg/j2k.c`

---

Hash: 004b47619573a582c076679764e07725ace3e497  

Date: Tue Feb 10 19:04:15 2026


---

### ts...@google.com (2026-02-10)

Actually merged to M145 as of the time of C17.

### sp...@google.com (2026-02-20)

** NOTE: This is an automatically generated email **

Hello,

Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $11000.00 for this report.

Rationale for this decision:
Renderer RCE / memory corruption in a sandboxed process


Important: This payment will be issued by Bugcrowd. You will receive an email from Bugcrowd in the next 24 hours which contains a submission you must claim to be rewarded.

If you do not receive an email from them, please check your spam folder and then reach out to us via a comment here. For issues related to Bugcrowd itself, please contact them via https://bugcrowd.com/support.


Thank you for your efforts and helping us make Chrome more secure for all users!

Cheers,
Chrome VRP Panel Bot


P.S. One other thing we'd like to mention:

* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.

Please contact security-vrp@chromium.org with any questions.

### jd...@google.com (2026-02-21)

Reward includes Bisect bonus

### ke...@gmail.com (2026-02-23)

Thanks, you missed my earlier comment? <https://issues.chromium.org/issues/477033835#comment13>

I wanted to donate to charity, can we still do that? I haven't claimed on bugcrowd yet.

### jd...@google.com (2026-03-02)

Hi, we are looking into this.

### ke...@gmail.com (2026-03-09)

Any update, will this work?

### ke...@gmail.com (2026-03-09)

Nevermind, i just received the e-mail about new rules, etc

### ch...@google.com (2026-05-14)

This bug has been closed for more than 14 weeks. Removing issue access restrictions.

## Bounty Award

> Renderer RCE / memory corruption in a sandboxed process

---
*Data from [Chromium Issue Tracker](https://issues.chromium.org/issues/477033835)*
