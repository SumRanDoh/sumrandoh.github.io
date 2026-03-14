(function ($) {
    "use strict";

    /*:::::::::::::::::::::::::::::::::::
       Navbar Area
    :::::::::::::::::::::::::::::::::::*/

     // Navbar Sticky
    $(window).scroll(function () {
        var scroll = $(window).scrollTop();

        if (scroll >= 1) {
            $(".navbar").addClass("bg-primari");
        } else {
            $(".navbar").removeClass("bg-primari");
        }
    });


    // Direct scroll (instant, no animation); offset so target isn't under sticky header
    // Collection section links (nav/dropdown) trigger expandCollectionSection so section uncollapses
    $(function () {
        $(document).on('click', '.nav-link, .smoth-scroll, .dropdown-item', function (event) {
            var $anchor = $(this);
            var href = $anchor.attr('href');
            if (href && href.indexOf('#') === 0) {
                var id = href.substring(1);
                if (id.indexOf('collection-') === 0) {
                    event.preventDefault();
                    $(document).trigger('expandCollectionSection', [id]);
                    return;
                }
                var $target = $(href);
                if ($target.length) {
                    var offset = ($('.navbar').length) ? $('.navbar').outerHeight() + 8 : 0;
                    $('html, body').scrollTop(Math.max(0, $target.offset().top - offset));
                    event.preventDefault();
                }
            }
        });
    });

    /*:::::::::::::::::::::::::::::::::::
       Collection sections: collapsed by default, click title to expand
       Next section title fixed to bottom; hide when top sticky enters bar zone or next section title is on screen
    ::::::::::::::::::::::::::::::::::::*/
    $(function () {
        var $sections = $('[data-collection-section]');
        var $toggles = $('.collection-section-toggle');
        var $bar = $('#collection-next-title-bar');
        if (!$bar.length) {
            $bar = $('<div id="collection-next-title-bar" class="collection-next-title-bar" role="button" tabindex="0" aria-label="Next collection category"></div>');
            $('body').append($bar);
        }

        /* Pin bar to visual viewport bottom on mobile (iOS Chrome/Safari: fixed is relative to layout viewport, so when browser UI hides the bar would stick too high) */
        function pinBarToVisualBottom() {
            var vv = window.visualViewport;
            if (!vv) return;
            var layoutH = document.documentElement.clientHeight;
            var bottomPx = layoutH - vv.offsetTop - vv.height;
            $bar.css('bottom', bottomPx + 'px');
        }
        if (typeof window.visualViewport !== 'undefined') {
            window.visualViewport.addEventListener('resize', pinBarToVisualBottom);
            window.visualViewport.addEventListener('scroll', pinBarToVisualBottom);
            pinBarToVisualBottom();
        }

        var BAR_HEIGHT = 64;
        var barPollTimer = null;
        var barRafId = null;
        /* Hysteresis (px) so we don't flip show/hide at exact boundary */
        var BAR_HYSTERESIS = 6;

        /* Debug: log title-label positions when ?debug=1; download with Cmd/Ctrl+Shift+L or the "Download position log" button */
        var positionLog = [];
        var positionLogMax = 2000;
        var lastLogTime = 0;
        var lastLogAction = null;
        var positionLogThrottleMs = 40;
        var positionLogThrottleWhenBarVisibleMs = 16;
        var positionLogActionThrottleMs = 200;
        var debugMode = typeof window !== 'undefined' && /[?&]debug=1/.test(window.location.search);
        function rectToObj(r) {
            return r ? { top: r.top, bottom: r.bottom, left: r.left, right: r.right, height: r.height, width: r.width } : null;
        }
        function capturePositionSnapshot(opts) {
            if (!debugMode) return;
            var now = Date.now();
            var action = opts && opts.action;
            if (action) {
                if (action === 'unstick' || action === 'restick' || action === 'barHide' || action === 'barShow') { /* always log */ }
                else if (action === lastLogAction && now - lastLogTime < positionLogActionThrottleMs) return;
            } else {
                var throttleMs = $bar.hasClass('is-visible') ? positionLogThrottleWhenBarVisibleMs : positionLogThrottleMs;
                if (now - lastLogTime < throttleMs) return;
            }
            lastLogTime = now;
            lastLogAction = action || null;
            var vh = window.innerHeight || document.documentElement.clientHeight;
            var barEl = $bar[0];
            var entry = {
                t: now,
                scrollY: window.pageYOffset || document.documentElement.scrollTop,
                viewportHeight: vh,
                stickyTopPx: 54,
                barZoneTop: vh - BAR_HEIGHT,
                barVisible: $bar.hasClass('is-visible'),
                barParent: barEl && barEl.parentNode ? (barEl.parentNode.id || barEl.parentNode.className || barEl.parentNode.tagName) : null,
                /* Title label positions (focus of log) */
                topStickyTitle: opts && opts.topStickyTitle ? opts.topStickyTitle : null,
                nextSectionTitle: opts && opts.nextSectionTitle ? opts.nextSectionTitle : null,
                bottomBar: null
            };
            if (barEl && barEl.getBoundingClientRect) {
                var r = barEl.getBoundingClientRect();
                entry.bottomBar = rectToObj(r);
            }
            if (opts) Object.keys(opts).forEach(function (k) {
                if (k !== 'topStickyTitle' && k !== 'nextSectionTitle') entry[k] = opts[k];
            });
            if (positionLog.length && positionLog[positionLog.length - 1].barVisible !== entry.barVisible) {
                entry.visibilityToggled = true;
            }
            positionLog.push(entry);
            if (positionLog.length > positionLogMax) positionLog.shift();
        }
        function downloadPositionLog() {
            var blob = new Blob([JSON.stringify(positionLog, null, 2)], { type: 'application/json' });
            var a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'collection-position-log-' + (new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)) + '.json';
            a.click();
            URL.revokeObjectURL(a.href);
        }
        if (debugMode) {
            $(document).on('keydown.positionLog', function (e) {
                if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.which === 76) {
                    e.preventDefault();
                    downloadPositionLog();
                }
            });
            var $btn = $('<button type="button" class="btn btn-sm btn-secondary" style="position:fixed;bottom:80px;right:16px;z-index:9999;">Download position log</button>');
            $btn.on('click', downloadPositionLog);
            $('body').append($btn);
        }
        function scheduleBarUpdate() {
            if (barRafId != null) return;
            barRafId = requestAnimationFrame(function () {
                barRafId = null;
                updateBarVisibility();
            });
        }

        /* Bar is always fixed at bottom; we only show/hide based on scroll position. No DOM moves, no timers. */
        function updateBarFromRects(expandedTitleRect, nextTitleRect) {
            var vh = window.innerHeight || document.documentElement.clientHeight;
            var barZoneTop = vh - BAR_HEIGHT;
            /* Hide when top sticky has scrolled into bar zone (hysteresis avoids boundary flicker) */
            var stickyInZone = expandedTitleRect && expandedTitleRect.bottom >= barZoneTop + BAR_HYSTERESIS;
            /* Hide when next section title is on screen (avoid duplicate label) */
            var nextOnScreen = nextTitleRect && nextTitleRect.top < vh - 30;
            if (stickyInZone || nextOnScreen) {
                if ($bar.hasClass('is-visible')) capturePositionSnapshot({ action: 'barHide' });
                $bar.removeClass('is-visible');
                return;
            }
            if (!$bar.hasClass('is-visible')) capturePositionSnapshot({ action: 'barShow' });
            $bar.addClass('is-visible');
        }

        function updateBarVisibility() {
            var $expanded = $('[data-collection-section].expanded');
            var $next = $expanded.next('[data-collection-section]');

            if (!$expanded.length || !$next.length) {
                if (debugMode) capturePositionSnapshot({ action: 'barHidden', expandedId: $expanded.length ? $expanded.attr('id') : null, nextId: $next.length ? $next.attr('id') : null });
                if ($bar.hasClass('is-visible')) capturePositionSnapshot({ action: 'barHide' });
                $bar.removeClass('is-visible');
                return;
            }
            var $expandedTitle = $expanded.find('.collection-section-toggle').first();
            var $nextTitle = $next.find('.collection-section-toggle').first();
            if (!$expandedTitle.length || !$nextTitle.length) {
                if (!$bar.hasClass('is-visible')) capturePositionSnapshot({ action: 'barShow' });
                $bar.addClass('is-visible');
                return;
            }
            var expandedTitleRect = $expandedTitle[0].getBoundingClientRect();
            var nextTitleRect = $nextTitle[0].getBoundingClientRect();
            if (debugMode) {
                capturePositionSnapshot({
                    expandedId: $expanded.attr('id'),
                    nextId: $next.attr('id'),
                    topStickyTitle: rectToObj(expandedTitleRect),
                    nextSectionTitle: rectToObj(nextTitleRect)
                });
            }
            updateBarFromRects(expandedTitleRect, nextTitleRect);
        }

        function expandSection(sectionId) {
            var $section = $('#' + sectionId);
            if (!$section.length) return;
            var wasExpanded = $section.hasClass('expanded');
            if (barPollTimer) {
                clearInterval(barPollTimer);
                barPollTimer = null;
            }
            $(window).off('scroll.collectionNextBar resize.collectionNextBar');
            $(document).off('scroll.collectionNextBar');
            $sections.removeClass('expanded');
            $toggles.attr('aria-expanded', 'false');
            if ($bar.parent()[0] !== document.body) {
                $('body').append($bar);
            }
            $bar.removeClass('is-visible').removeData('section-id').off('click keydown');
            if (wasExpanded) {
                var offset = ($('.navbar').length) ? $('.navbar').outerHeight() + 8 : 0;
                $('html, body').scrollTop(Math.max(0, $section.offset().top - offset));
                return;
            }
            $section.addClass('expanded');
            $section.find('.collection-section-toggle').attr('aria-expanded', 'true');
            var $next = $section.next('[data-collection-section]');
            if ($next.length) {
                var titleText = $next.find('.collection-section-toggle').first().text().trim();
                $bar.text(titleText).data('section-id', $next.attr('id'));
                $bar.on('click', function () {
                    expandSection($next.attr('id'));
                });
                $bar.on('keydown', function (e) {
                    if (e.which === 13 || e.which === 32) {
                        e.preventDefault();
                        expandSection($next.attr('id'));
                    }
                });
                $(window).on('scroll.collectionNextBar', scheduleBarUpdate);
                $(document).on('scroll.collectionNextBar', scheduleBarUpdate);
                $(window).on('resize.collectionNextBar', scheduleBarUpdate);
                barPollTimer = setInterval(updateBarVisibility, 50);
                updateBarVisibility();
            }
            var offset = ($('.navbar').length) ? $('.navbar').outerHeight() + 8 : 0;
            $('html, body').scrollTop(Math.max(0, $section.offset().top - offset));
        }

        $(document).on('expandCollectionSection', function (e, sectionId) {
            expandSection(sectionId);
        });

        $toggles.on('click', function () {
            var sectionId = $(this).data('section-id');
            if (sectionId) expandSection(sectionId);
        });
        $toggles.on('keydown', function (e) {
            if (e.which === 13 || e.which === 32) {
                e.preventDefault();
                var sectionId = $(this).data('section-id');
                if (sectionId) expandSection(sectionId);
            }
        });
    });


    /*::::::::::::::::::::::::::::::::::::
       Contact Area 
    ::::::::::::::::::::::::::::::::::::*/
    var form = $('#contact-form');

    var formMessages = $('.form-message');
    $(form).submit(function (e) {
        e.preventDefault();
        var formData = $(form).serialize();
        $.ajax({
                type: 'POST',
                url: $(form).attr('action'),
                data: formData
            })
            .done(function (response) {
                $(formMessages).removeClass('error');
                $(formMessages).addClass('success');
                $(formMessages).text(response);

                $('#contact-form input,#contact-form textarea').val('');
            })
            .fail(function (data) {
                $(formMessages).removeClass('success');
                $(formMessages).addClass('error');

                if (data.responseText !== '') {
                    $(formMessages).text(data.responseText);
                } else {
                    $(formMessages).text('Oops! An error occured and your message could not be sent.');
                }
            });
    });
    
    
    /*::::::::::::::::::::::::::::::::::::
    Preloader
    ::::::::::::::::::::::::::::::::::::*/
    $(window).on('load', function () {
        $('.preloader').fadeOut();
    });

}(jQuery));
