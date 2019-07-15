const mix = require('laravel-mix');

/*
 |--------------------------------------------------------------------------
 | Mix Asset Management
 |--------------------------------------------------------------------------
 |
 | Mix provides a clean, fluent API for defining some Webpack build steps
 | for your Laravel application. By default, we are compiling the Sass
 | file for the application as well as bundling up all the JS files.
 |
 */

mix.js(['resources/js/app.js', 'resources/js/sb-admin-2.js'], 'public/js')
        .extract([
            'vue',
            'bootstrap',
            'selectize',
            'list.js',
            'datatables.net',
            'datatables.net-bs4',
            'jquery',
            'jquery.easing',
            'chart.js',
            '@fortawesome/fontawesome-free',
            'bootstrap-select',
            'mapbox-gl',
            'bootstrap-datepicker',
            'summernote'
        ]);

mix.sass('resources/sass/app.scss', 'public/css/app.css');
mix.less('node_modules/selectize/dist/less/selectize.less', 'public/css/vendor.css');
mix.combine([
    'public/css/vendor.css',
    'node_modules/bootstrap/dist/css/bootstrap.min.css',
    'node_modules/datatables.net-bs4/css/*.css',
    'node_modules/@fortawesome/fontawesome-free/css/*.css',
    'node_modules/bootstrap-select/dist/css/bootstrap-select.css',
    'node_modules/mapbox-gl/dist/mapbox-gl.css',
    'node_modules/bootstrap-datepicker/dist/css/bootstrap-datepicker3.css',
    'node_modules/summernote/dist/summernote.css',
], 'public/css/vendor.css');
mix.copyDirectory('node_modules/@fortawesome/fontawesome-free/webfonts', 'public/webfonts');
mix.copyDirectory('node_modules/summernote/dist/font', 'public/css/font');

if (mix.inProduction()) {
    mix.version();
}


mix.browserSync('127.0.0.1:8000');
