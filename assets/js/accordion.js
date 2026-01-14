function snapPixelArtToColumn(imgEl) {
  if (!imgEl || !imgEl.naturalWidth || !imgEl.naturalHeight) return;

  const col = imgEl.parentElement;
  const colW = col.clientWidth;

  const nw = imgEl.naturalWidth;
  const nh = imgEl.naturalHeight;

  const MAX_SIDE = 692;

  // Limits on scale
  const maxScaleByCol = colW / nw;
  const maxScaleByCap = MAX_SIDE / Math.max(nw, nh);
  const maxAllowedScale = Math.min(1, maxScaleByCol, maxScaleByCap);

  // Pick largest power-of-two scale <= maxAllowedScale
  let scale = 1;
  while (scale / 2 >= maxAllowedScale) scale /= 2;

  const w = Math.max(1, Math.floor(nw * scale));

  imgEl.style.width = w + "px";
  imgEl.style.height = w + "px";
}

$(function () {
  const $img = $("#prismatics-image");

  function setAndSnap(src) {
    // Wait for the new image to load so naturalWidth is correct
    $img.off("load._snap").on("load._snap", function () {
      snapPixelArtToColumn(this);
    });
    $img.attr("src", src);
  }

  // When a panel opens, swap image + snap size
  $("#accordion .collapse").on("shown.bs.collapse", function () {
    const src = $(this).data("image");
    if (src) setAndSnap(src);
  });

  // Initialize from the open panel on load
  const $open = $("#accordion .collapse.show").first();
  if ($open.length) {
    const src = $open.data("image");
    if (src) setAndSnap(src);
  } else {
    // Fallback: snap whatever is already there
    snapPixelArtToColumn($img.get(0));
  }

  // Re-snap on resize (so it stays pixel-perfect when the column width changes)
  $(window).on("resize", function () {
    snapPixelArtToColumn($img.get(0));
  });
});

// $(function () {
//   const $accordion = $("#accordion");

//   // Prevent the accordion from ending up with nothing open
//   $accordion.on("hide.bs.collapse", ".collapse", function (e) {
//     // If this is the ONLY open panel, cancel the hide
//     if ($accordion.find(".collapse.show").length === 1) {
//       e.preventDefault();
//     }
//   });

//   // (Optional) If for any reason none are open on load, open the first
//   if ($accordion.find(".collapse.show").length === 0) {
//     $accordion.find(".collapse").first().collapse("show");
//   }
// });