<?php

namespace App;

use Illuminate\Notifications\Notifiable;
use Illuminate\Contracts\Auth\MustVerifyEmail;
use Illuminate\Foundation\Auth\User as Authenticatable;

class User extends Authenticatable implements MustVerifyEmail
{
    use Notifiable;

    /**
     * The attributes that are mass assignable.
     *
     * @var array
     */
    protected $fillable = [
        'forename', 'surname', 'middle_initials', 'email', 'password',
    ];

    /**
     * The attributes that should be hidden for arrays.
     *
     * @var array
     */
    protected $hidden = [
        'password', 'remember_token',
    ];

    /**
     * The attributes that should be cast to native types.
     *
     * @var array
     */
    protected $casts = [
        'email_verified_at' => 'datetime',
    ];

    public function subscriptions()
    {
        return $this->belongsToMany('App\Board', 'board_subscriptions')
                    ->using('App\BoardSubscription')
                    ->withTimestamps();
    }

    public function getNameAttribute()
    {
        return $this->attributes['forename'] . ' ' .
               $this->attributes['middle_initials'] . ' ' . // TODO: guard for empty
               $this->attributes['surname'];
    }
}
