<?php

namespace App\Providers;

use Illuminate\Support\ServiceProvider;
use Illuminate\Support\Facades\Blade;
use App\Board;

class BladeDirectiveServiceProvider extends ServiceProvider
{
    /**
     * Register services.
     *
     * @return void
     */
    public function register()
    {
        //
    }

    /**
     * Bootstrap services.
     *
     * @return void
     */
    public function boot()
    {
        Blade::if('subscriber', function (Board $board) {
            return $board->isSubscribed();
        });

        Blade::if('member', function (Board $board) {
            return $board->isMember();
        });

        Blade::if('committee', function (Board $board) {
            return $board->isCommittee();
        });

        Blade::if('admin', function (Board $board) {
            return $board->isAdmin();
        });
    }
}