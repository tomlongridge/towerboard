<?php

namespace App;

use Illuminate\Database\Eloquent\Model;

class Tower extends Model
{
    public function boards()
    {
        return $this->hasMany(Board::class);
    }

    public function getName()
    {
        return $this->attributes['town'] .
               ($this->attributes['area'] ? ' (' . $this->attributes['area'] . ')' : '') .
               ', ' . $this->attributes['county'] .
               ', ' . $this->attributes['country'];
    }
}
