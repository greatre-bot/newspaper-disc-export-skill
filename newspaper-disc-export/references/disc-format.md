# Known disc format and safeguards

## Known layout

The first two verified discs used:

```text
<drive>\
├─ autorun.inf
├─ autorun.exe
└─ 019Z\<eight U+007F characters>\
   ├─ autorun.exe
   ├─ Form\
   └─ pic\YYYY\MM\DD\NN.jpg
```

The root launcher builds the hidden path and starts the second executable. Direct execution is unnecessary because the original JPEGs are reachable through the hidden path.

## JPEG compatibility issue

All verified newspaper JPEGs began with:

```text
FF D8 FF D9 FF D8 FF E0
```

The first `FF D8 FF D9` is an empty JPEG. Pillow tolerates it, but PDF DCT decoders may render a blank page when the entire file is embedded. For the PDF-embedded copy only, remove the first four bytes when this exact signature is present. Do not modify the source JPEG and do not recompress pixels.

## Validation

- Verify each source image with Pillow.
- Create PDFs with the actual image aspect ratio and DPI.
- Require one `/DCTDecode` image per PDF page.
- Compare SHA256 of each embedded raw DCT stream with the corresponding source JPEG after the four-byte compatibility trim.
- Require PDF page count to equal the number of numerically sorted edition files.
- Treat missing edition numbers as an anomaly. Do not renumber later editions.
- Treat missing calendar dates as source gaps, not proof that publication was expected.
- Preserve landscape pages. A disc may contain a single landscape supplement page on many dates.

## Changed formats

If the known `019Z` path is absent, recursively inventory the optical drive read-only and search for numeric `YYYY\MM\DD\NN.jpg` structures, databases, indexes, or data containers. Do not run executables or use GUI screenshots until direct image and container analysis is exhausted.

## Poppler on Windows

Some Windows Poppler builds mishandle Chinese source paths. For visual QA only, copy the finished sample PDF to an ASCII-only temporary path, render it there, and leave the final PDF in the required Chinese output path.

