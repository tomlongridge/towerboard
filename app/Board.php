<?php

namespace App;

use App\User;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;

class Board extends Model
{
    use SoftDeletes;

    protected $guarded = ['id'];

    public function getRouteKeyName()
    {
        return 'name';
    }

    protected static function boot()
    {
        parent::boot();

        static::deleting(function ($board) {
            // Remove all associated notices and subscriptions
            $board->notices()->delete();
            BoardAffiliate::where('board_id', $board->id)->delete();
            BoardSubscription::where('board_id', $board->id)->delete();
        });
    }

    public function addNotice(array $fields)
    {
        return Notice::create(array_merge($fields, ['board_id' => $this->id]));
    }

    public function subscribe(User $user)
    {
        BoardSubscription::create([
            'user_id' => $user->id,
            'board_id' => $this->id
        ]);
    }

    public function isSubscribed(?User $user)
    {
        if ($user == null) {
            return false;
        } else {
            return $this->subscribers()->where('id', $user->id)->exists();
        }
    }

    public function notices()
    {
        return $this->hasMany(Notice::class);
    }

    public function owner()
    {
        return $this->belongsTo(User::class);
    }

    public function tower()
    {
        return $this->belongsTo(Tower::class);
    }

    public function subscribers()
    {
        return $this->belongsToMany('App\User', 'board_subscriptions')
                    ->using('App\BoardSubscription')
                    ->withTimestamps();
    }

    public function affiliates()
    {
        return $this->belongsToMany('App\Board', 'board_affiliates', 'affiliate_id', 'board_id')
                    ->using('App\BoardAffiliate')
                    ->withTimestamps();
    }

    public function affiliatedTo()
    {
        return $this->belongsToMany('App\Board', 'board_affiliates', 'board_id', 'affiliate_id')
                    ->using('App\BoardAffiliate')
                    ->withTimestamps();
    }
}
