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
    $(function () {
        $('.nav-link, .smoth-scroll, .dropdown-item').on('click', function (event) {
            var $anchor = $(this);
            var href = $anchor.attr('href');
            if (href && href.indexOf('#') === 0) {
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
       Next section title fixed to bottom of screen when a non-last category is expanded
    ::::::::::::::::::::::::::::::::::::*/
    $(function () {
        var $sections = $('[data-collection-section]');
        var $toggles = $('.collection-section-toggle');
        var $bar = $('#collection-next-title-bar');
        if (!$bar.length) {
            $bar = $('<div id="collection-next-title-bar" class="collection-next-title-bar" role="button" tabindex="0" aria-label="Next collection category"></div>');
            $('body').append($bar);
        }

        function expandSection(sectionId) {
            $sections.removeClass('expanded');
            $toggles.attr('aria-expanded', 'false');
            $bar.removeClass('is-visible').removeData('section-id').off('click keydown');
            var $section = $('#' + sectionId);
            if ($section.length) {
                $section.addClass('expanded');
                $section.find('.collection-section-toggle').attr('aria-expanded', 'true');
                var $next = $section.next('[data-collection-section]');
                if ($next.length) {
                    var titleText = $next.find('.collection-section-toggle').first().text().trim();
                    $bar.text(titleText).data('section-id', $next.attr('id')).addClass('is-visible');
                    $bar.on('click', function () {
                        expandSection($next.attr('id'));
                    });
                    $bar.on('keydown', function (e) {
                        if (e.which === 13 || e.which === 32) {
                            e.preventDefault();
                            expandSection($next.attr('id'));
                        }
                    });
                }
                var offset = ($('.navbar').length) ? $('.navbar').outerHeight() + 8 : 0;
                $('html, body').scrollTop(Math.max(0, $section.offset().top - offset));
            }
        }

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
