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
       Next section title fixed to bottom; unstick when top title scrolls down to it or next title scrolls up into view
    ::::::::::::::::::::::::::::::::::::*/
    $(function () {
        var $sections = $('[data-collection-section]');
        var $toggles = $('.collection-section-toggle');
        var $bar = $('#collection-next-title-bar');
        if (!$bar.length) {
            $bar = $('<div id="collection-next-title-bar" class="collection-next-title-bar" role="button" tabindex="0" aria-label="Next collection category"></div>');
            $('body').append($bar);
        }

        var BAR_HEIGHT = 64;
        var barPollTimer = null;
        var barRafId = null;
        function scheduleBarUpdate() {
            if (barRafId != null) return;
            barRafId = requestAnimationFrame(function () {
                barRafId = null;
                updateBarVisibility();
            });
        }

        function updateBarFromRects(expandedTitleRect, nextTitleRect) {
            var viewportBottom = window.innerHeight || document.documentElement.clientHeight;
            var threshold = viewportBottom - BAR_HEIGHT;
            if (expandedTitleRect && expandedTitleRect.bottom >= threshold) {
                $bar.removeClass('is-visible');
                return;
            }
            if (nextTitleRect && nextTitleRect.top <= threshold) {
                $bar.removeClass('is-visible');
                return;
            }
            $bar.addClass('is-visible');
        }

        function updateBarVisibility() {
            var $expanded = $('[data-collection-section].expanded');
            var $next = $expanded.next('[data-collection-section]');
            if (!$expanded.length || !$next.length) {
                $bar.removeClass('is-visible');
                return;
            }
            var $expandedTitle = $expanded.find('.collection-section-toggle').first();
            var $nextTitle = $next.find('.collection-section-toggle').first();
            if (!$expandedTitle.length || !$nextTitle.length) {
                $bar.addClass('is-visible');
                return;
            }
            var expandedTitleRect = $expandedTitle[0].getBoundingClientRect();
            var nextTitleRect = $nextTitle[0].getBoundingClientRect();
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
            $bar.removeClass('is-visible').removeData('section-id').off('click keydown');
            if (wasExpanded) return;
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
                barPollTimer = setInterval(updateBarVisibility, 120);
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
