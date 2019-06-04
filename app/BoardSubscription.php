<?php

namespace App;

use App\Board;
use App\Notice;
use App\User;

use Illuminate\Database\Eloquent\Relations\Pivot;

class BoardSubscription extends Pivot
{
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
