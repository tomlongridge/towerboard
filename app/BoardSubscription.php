<?php

namespace App;

use App\Board;
use App\Notice;
use App\User;

use BenSampo\Enum\Traits\CastsEnums;

use Illuminate\Database\Eloquent\Relations\Pivot;
use App\Enums\SubscriptionType;

class BoardSubscription extends Pivot
{
    use CastsEnums;

    protected $enumCasts = [
        'type' => SubscriptionType::class
    ];

    public $table = 'board_subscriptions';

    public function board()
    {
        return $this->belongsTo(Board::class);
    }

    public function subscriber()
    {
        return $this->belongsTo(User::class);
    }

    public function notices()
    {
        return $this->hasManyThrough(Notice::class, Board::class);
    }
}
