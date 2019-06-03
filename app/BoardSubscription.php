<?php

namespace App;

use Illuminate\Database\Eloquent\Relations\Pivot;

class BoardSubscription extends Pivot
{
    public $table = 'board_subscriptions';
}
