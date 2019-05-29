<?php

namespace App\Providers;

use App\Guild;

use \Cache;
use Illuminate\Support\ServiceProvider;

class CreateGuildCache extends ServiceProvider
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
        Cache::remember('guilds', (60 * 24), function () {
            return Guild::with('affiliates', 'affiliatedTo')->get();
        });
    }
}
