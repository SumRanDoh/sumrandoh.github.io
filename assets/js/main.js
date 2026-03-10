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


    // Direct scroll (instant, no animation)
    $(function () {
        $('.nav-link, .smoth-scroll').on('click', function (event) {
            var $anchor = $(this);
            var href = $anchor.attr('href');
            if (href && href.indexOf('#') === 0) {
                var $target = $(href);
                if ($target.length) {
                    $('html, body').scrollTop($target.offset().top);
                    event.preventDefault();
                }
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
