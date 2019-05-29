<?php

namespace App;

use Illuminate\Database\Eloquent\Model;

class Guild extends Model
{
    public function towers()
    {
        return $this->hasMany(Tower::class);
    }

    public function affiliatedTo() {
        return $this->belongsTo(Guild::class, 'affiliated_to', 'id');
    }

    public function affiliates() {
        return $this->hasMany(Guild::class, 'affiliated_to', 'id');
    }
}
