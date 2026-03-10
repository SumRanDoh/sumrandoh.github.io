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
  const $imgs = $(".prismatics-screenshot");

  function snapAll() {
    $imgs.each(function () {
      snapPixelArtToColumn(this);
    });
  }

  $imgs.on("load", function () {
    snapPixelArtToColumn(this);
  });

  // Snap on load (images may already be cached)
  snapAll();

  $(window).on("resize", snapAll);
});