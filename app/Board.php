<?php

namespace App;

use App\User;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;
use App\Enums\SubscriptionType;

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
        return Notice::create(
            array_merge(
                $fields,
                [
                    'board_id' => $this->id,
                    'created_by' => auth()->id(),
                ]
            )
        );
    }

    public function subscribe(User $user, $type = null)
    {
        BoardSubscription::create([
            'user_id' => $user->id,
            'board_id' => $this->id,
            'type' => $type
        ]);
    }

    public function getSubscription(User $user = null, $type = SubscriptionType::BASIC)
    {
        if ($user == null) {
            $user = auth()->user();
        }

        if ($user == null) {
            return null;
        }

        $subscription = $this->subscribers()
            ->where('id', $user->id)
            ->wherePivot('type', '>=', $type)
            ->first();

        return $subscription? $subscription->subscription : null;
    }

    public function isSubscribed(User $user = null, $type = SubscriptionType::BASIC)
    {
        return $this->getSubscription($user, $type) != null;
    }

    public function isMember(User $user = null)
    {
        return $this->isSubscribed($user, SubscriptionType::MEMBER);
    }

    public function isCommittee(User $user = null)
    {
        return $this->isSubscribed($user, SubscriptionType::COMMITTEE);
    }

    public function isAdmin(User $user = null)
    {
        return $this->isSubscribed($user, SubscriptionType::ADMIN);
    }

    public function notices()
    {
        return $this->hasMany(Notice::class);
    }

    public function tower()
    {
        return $this->belongsTo(Tower::class);
    }

    public function subscribers()
    {
        return $this->belongsToMany('App\User', 'board_subscriptions')
                    ->using('App\BoardSubscription')
                    ->withPivot('type')
                    ->as('subscription')
                    ->withTimestamps();
    }

    public function members()
    {
        return $this->subscribers()
            ->wherePivot('type', '>=', SubscriptionType::MEMBER);
    }

    public function administrators()
    {
        return $this->subscribers()
            ->wherePivot('type', '>=', SubscriptionType::ADMIN);
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
