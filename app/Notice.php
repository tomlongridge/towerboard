<?php

namespace App;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;


class Notice extends Model
{
    use SoftDeletes;

    protected $guarded = ['id'];

    public function board()
    {
        return $this->belongsTo(Board::class);
    }
}
