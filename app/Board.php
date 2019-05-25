<?php

namespace App;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;


class Board extends Model
{
    use SoftDeletes;

    protected $guarded = ['id'];

    protected static function boot()
    {
        parent::boot();

        static::deleting(function($board) {
            $board->notices()->delete();
        });
    }

    public function addNotice(array $fields) {
        return Notice::create(array_merge($fields, ['board_id' => $this->id]));
    }

    public function notices()
    {
        return $this->hasMany(Notice::class);
    }

    public function owner()
    {
        return $this->belongsTo(User::class);
    }
}
