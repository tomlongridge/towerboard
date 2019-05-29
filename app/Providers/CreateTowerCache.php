<?php

namespace App\Providers;

use \Cache;
use App\Tower;
use Illuminate\Support\ServiceProvider;

class CreateTowerCache extends ServiceProvider
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
        Cache::remember('towers', (60 * 24), function () {
            return Tower::all();
        });
    }
}
