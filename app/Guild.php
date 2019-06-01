<?php

namespace App;

use Illuminate\Database\Eloquent\Model;

class Guild extends Model
{
    public function affiliatedTo()
    {
        return $this->belongsTo(Guild::class, 'affiliated_to', 'id');
    }

    public function affiliates()
    {
        return $this->hasMany(Guild::class, 'affiliated_to', 'id');
    }

    public function boards()
    {
        return optional(Board::whereNull('tower_id')->where('guild_id', $this->id))->get();
    }

    public function affiliatedBoards()
    {
        return $this->hasMany(Board::class);
    }
}
