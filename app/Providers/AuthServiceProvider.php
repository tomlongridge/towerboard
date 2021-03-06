<?php

namespace App\Providers;

use Illuminate\Support\Facades\Gate;
use Illuminate\Foundation\Support\Providers\AuthServiceProvider as ServiceProvider;

class AuthServiceProvider extends ServiceProvider
{
    /**
     * The policy mappings for the application.
     *
     * @var array
     */
    protected $policies = [
        'App\Board' => 'App\Policies\BoardPolicy',
        'App\Notice' => 'App\Policies\NoticePolicy',
        'App\BoardSubscription' => 'App\Policies\SubscriptionPolicy',
        'App\BoardRole' => 'App\Policies\BoardRolePolicy',
    ];

    /**
     * Register any authentication / authorization services.
     *
     * @return void
     */
    public function boot()
    {
        $this->registerPolicies();

        //
    }
}
